import asyncio
import contextlib
import re
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import parse_qs, urlsplit

from playwright.async_api import BrowserContext, Page, Playwright, TimeoutError as PlaywrightTimeoutError

from ..accounts import Account
from ..cancellation import CancellationToken
from ..integrations.oauth_callback import CallbackServer
from .errors import AuthErrorCode, MESSAGES, classify_text
from .response_observer import ResponseObserver
from .selectors import blocker, email_input, first_visible, otp_input, password_input, visible_error_text
from .totp import fetch_token


class ResultCode(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DASHBOARD_AUTH_REQUIRED = "dashboard_auth_required"
    DASHBOARD_AUTH_FAILED = "dashboard_auth_failed"
    CAPTCHA_REQUIRED = "captcha_required"
    PHONE_VERIFICATION_REQUIRED = "phone_verification_required"
    INVALID_EMAIL = "invalid_email"
    INVALID_PASSWORD = "invalid_password"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_DISABLED = "account_disabled"
    RATE_LIMITED = "rate_limited"
    INVALID_OTP = "invalid_otp"
    EXPIRED_OTP = "expired_otp"
    LOGIN_REJECTED = "login_rejected"


@dataclass(frozen=True, slots=True)
class AccountResult:
    account: Account
    code: ResultCode
    detail: str = ""


class FlowStopped(RuntimeError):
    def __init__(self, code: ResultCode, detail: str) -> None:
        super().__init__(detail)
        self.code = code


async def _click_continue(page: Page) -> None:
    button = await first_visible(
        page.get_by_role("button", name=re.compile(r"^(continue|next|submit|verify)$", re.I)),
        page.locator('button[type="submit"]'),
    )
    if not button:
        raise FlowStopped(ResultCode.FAILED, "không tìm thấy nút tiếp tục")
    await button.click()


async def _login_dashboard(page: Page, password: str | None, token: CancellationToken) -> None:
    if url_path(page.url) != "/login":
        return
    if not password:
        raise FlowStopped(ResultCode.DASHBOARD_AUTH_REQUIRED, "cần mật khẩu dashboard 9router")
    token.raise_if_cancelled()
    password_field = await password_input(page, timeout=10_000)
    if not password_field:
        raise FlowStopped(ResultCode.DASHBOARD_AUTH_FAILED, "9router không hỗ trợ đăng nhập mật khẩu")
    await password_field.fill(password)
    await page.get_by_role("button", name="Login", exact=True).click()
    try:
        await page.wait_for_url(re.compile(r"/dashboard(?:/|$)"), timeout=15_000)
    except PlaywrightTimeoutError as error:
        body = (await page.locator("body").inner_text()).lower()
        detail = "dashboard bị khóa tạm thời" if "locked" in body else "mật khẩu dashboard không đúng"
        raise FlowStopped(ResultCode.DASHBOARD_AUTH_FAILED, detail) from error


def _raise_auth_error(code: AuthErrorCode) -> None:
    raise FlowStopped(ResultCode(code.value), MESSAGES[code])


async def _auth_error(page: Page, observer: ResponseObserver) -> AuthErrorCode | None:
    ui_error = classify_text(await visible_error_text(page))
    if ui_error:
        return ui_error
    signal = observer.latest()
    return signal.code if signal else None


async def _wait_after_submit(
    page: Page, observer: ResponseObserver, token: CancellationToken, timeout: float = 2
) -> AuthErrorCode | None:
    deadline = asyncio.get_running_loop().time() + timeout
    try:
        while asyncio.get_running_loop().time() < deadline:
            token.raise_if_cancelled()
            error = await _auth_error(page, observer)
            if error:
                return error
            if page.url.startswith("http://localhost:1455/"):
                return None
            await page.wait_for_timeout(200)
        return None
    finally:
        observer.stop_step()


async def _submit_otp(
    page: Page,
    account: Account,
    token: CancellationToken,
    observer: ResponseObserver,
) -> None:
    for attempt in range(2):
        otp = await otp_input(page, timeout=2_000)
        if not otp:
            return
        await otp.fill(await fetch_token(account.two_factor_secret, next_window=attempt > 0))
        observer.start_step()
        await _click_continue(page)
        error = await _wait_after_submit(page, observer, token)
        if error == AuthErrorCode.EXPIRED_OTP and attempt == 0:
            continue
        if error:
            _raise_auth_error(error)
        return


async def _complete_openai_login(page: Page, account: Account, token: CancellationToken) -> None:
    observer = ResponseObserver(page)
    deadline = asyncio.get_running_loop().time() + 300
    email_done = password_done = otp_done = False
    while asyncio.get_running_loop().time() < deadline:
        token.raise_if_cancelled()
        if page.url.startswith("http://localhost:1455/"):
            return
        error = classify_text(await visible_error_text(page))
        if error:
            _raise_auth_error(error)
        blocked = await blocker(page)
        if blocked == "phone":
            raise FlowStopped(ResultCode.PHONE_VERIFICATION_REQUIRED, "cần xác minh số điện thoại thủ công")
        if blocked == "captcha":
            raise FlowStopped(ResultCode.CAPTCHA_REQUIRED, "cần xác minh CAPTCHA thủ công")

        email = await email_input(page, timeout=700)
        if email and not email_done:
            await email.click()
            await email.fill("")
            await email.type(account.email, delay=30)
            await page.wait_for_timeout(1000)
            observer.start_step()
            await _click_continue(page)
            error = await _wait_after_submit(page, observer, token)
            if error:
                _raise_auth_error(error)
            email_done = True
            continue
        password = await password_input(page, timeout=700)
        if password and not password_done:
            await password.fill(account.password)
            observer.start_step()
            await _click_continue(page)
            error = await _wait_after_submit(page, observer, token)
            if error:
                _raise_auth_error(error)
            password_done = True
            continue
        if await otp_input(page, timeout=700) and not otp_done:
            await _submit_otp(page, account, token, observer)
            otp_done = True
            continue
        await page.wait_for_timeout(500)
    raise FlowStopped(ResultCode.FAILED, "hết thời gian đăng nhập OpenAI")


async def _open_oauth(context: BrowserContext, host: str) -> tuple[Page, str]:
    async def _fetch_api() -> dict[str, object]:
        cookies = await context.cookies(host)
        cookie_header = "; ".join(f"{c['name']}={c['value']}" for c in cookies) if cookies else ""

        def _do_request() -> bytes:
            import urllib.parse
            import urllib.request
            redirect_uri = urllib.parse.quote("http://localhost:1455/auth/callback", safe="")
            req = urllib.request.Request(f"{host}/api/oauth/codex/authorize?redirect_uri={redirect_uri}")
            if cookie_header:
                req.add_header("Cookie", cookie_header)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read()

        data_bytes = await asyncio.to_thread(_do_request)
        import json
        return json.loads(data_bytes.decode())

    try:
        auth_data = await _fetch_api()
    except Exception as error:
        raise FlowStopped(ResultCode.FAILED, f"không thể kết nối API 9router: {error}") from error

    auth_url = auth_data.get("authUrl")
    state = auth_data.get("state")
    if not isinstance(auth_url, str) or not isinstance(state, str) or not auth_url or not state:
        raise FlowStopped(ResultCode.FAILED, "9router không trả về OAuth URL hoặc state")
    oauth_page = await context.new_page()
    await oauth_page.goto(auth_url, wait_until="domcontentloaded")
    return oauth_page, state


async def run_account(
    playwright: Playwright,
    account: Account,
    host: str,
    callback_server: CallbackServer,
    token: CancellationToken,
    dashboard_password: str | None = None,
    headless: bool = False,
) -> AccountResult:
    browser = None
    callback_task: asyncio.Task[str] | None = None
    callback_state: str | None = None
    try:
        token.raise_if_cancelled()
        browser = await playwright.chromium.launch(
            channel="chrome",
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context()
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        dashboard = await context.new_page()
        await dashboard.goto(f"{host}/dashboard/providers/codex", wait_until="domcontentloaded")
        await _login_dashboard(dashboard, dashboard_password, token)

        oauth_page, callback_state = await _open_oauth(context, host)
        callback_server.expect(callback_state)
        callback_task = asyncio.create_task(callback_server.wait(callback_state))
        await _complete_openai_login(oauth_page, account, token)
        callback_url = await callback_task
        token.raise_if_cancelled()

        callback_params = parse_qs(urlsplit(callback_url).query)
        if callback_params.get("error"):
            error_desc = callback_params.get("error_description", ["OAuth error"])[0]
            raise FlowStopped(ResultCode.FAILED, f"OpenAI từ chối ủy quyền: {error_desc}")
        if not callback_params.get("code"):
            raise FlowStopped(ResultCode.FAILED, "callback thiếu mã ủy quyền OAuth")

        dialog = dashboard.get_by_role("dialog")
        await dialog.locator('input:not([readonly])').fill(callback_url)
        await dialog.get_by_role("button", name="Connect", exact=True).click()
        success = dialog.get_by_text("Connected Successfully!", exact=True)
        failure = dialog.get_by_text("Connection Failed", exact=True)
        await success.or_(failure).wait_for(state="visible", timeout=60_000)
        if await failure.is_visible():
            raise FlowStopped(ResultCode.FAILED, "9router báo kết nối thất bại")
        return AccountResult(account, ResultCode.SUCCESS)
    except asyncio.CancelledError:
        return AccountResult(account, ResultCode.CANCELLED, "đã dừng theo yêu cầu")
    except FlowStopped as error:
        return AccountResult(account, error.code, str(error))
    except Exception as error:
        return AccountResult(account, ResultCode.FAILED, type(error).__name__)
    finally:
        if callback_task and not callback_task.done():
            callback_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await callback_task
        if callback_state:
            callback_server.discard(callback_state)
        if browser:
            await browser.close()


def url_path(url: str) -> str:
    return urlsplit(url).path.rstrip("/") or "/"
            with contextlib.suppress(asyncio.CancelledError):
                await callback_task
        if callback_state:
            callback_server.discard(callback_state)
        if browser:
            await browser.close()


def url_path(url: str) -> str:
    return urlsplit(url).path.rstrip("/") or "/"
