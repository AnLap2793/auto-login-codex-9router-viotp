"""Điều phối một tài khoản: mở Chrome riêng, đăng nhập, nhận callback, gắn vào 9router.

Các bước chi tiết nằm ở `dashboard_login`, `openai_login` và `oauth_flow`.
Module này chỉ ghép chúng lại và bảo đảm luôn dọn dẹp Chrome.
"""

import asyncio
import contextlib

from playwright.async_api import Playwright

from ..accounts import Account
from ..cancellation import CancellationToken
from ..integrations.oauth_callback import CallbackServer
from .dashboard_login import login_dashboard, url_path
from .oauth_flow import open_oauth, verify_callback
from .openai_login import complete_openai_login
from .results import AccountResult, FlowStopped, ProgressCallback, ResultCode

CONNECT_TIMEOUT_MS = 60_000

# Tên riêng tư giữ lại cho test và mã gọi cũ.
_login_dashboard = login_dashboard
_open_oauth = open_oauth
_complete_openai_login = complete_openai_login

__all__ = [
    "AccountResult",
    "FlowStopped",
    "ResultCode",
    "run_account",
    "url_path",
]


async def _attach_to_dashboard(dashboard, callback_url: str) -> None:
    """Dán callback URL vào modal của 9router và chờ kết quả kết nối."""
    dialog = dashboard.get_by_role("dialog")
    await dialog.locator("input:not([readonly])").fill(callback_url)
    await dialog.get_by_role("button", name="Connect", exact=True).click()
    success = dialog.get_by_text("Connected Successfully!", exact=True)
    failure = dialog.get_by_text("Connection Failed", exact=True)
    await success.or_(failure).wait_for(state="visible", timeout=CONNECT_TIMEOUT_MS)
    if await failure.is_visible():
        raise FlowStopped(ResultCode.FAILED, "9router báo kết nối thất bại")


async def run_account(
    playwright: Playwright,
    account: Account,
    host: str,
    callback_server: CallbackServer,
    token: CancellationToken,
    dashboard_password: str | None = None,
    headless: bool = False,
    manual_timeout: float = 0,
    on_progress: ProgressCallback | None = None,
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
        await login_dashboard(dashboard, dashboard_password, token)

        oauth_page, callback_state = await open_oauth(context, host, callback_server.port)
        callback_server.expect(callback_state)
        callback_task = asyncio.create_task(callback_server.wait(callback_state))
        await complete_openai_login(
            oauth_page, account, token, callback_server.port, manual_timeout, on_progress
        )
        callback_url = await callback_task
        token.raise_if_cancelled()

        verify_callback(callback_url)
        await _attach_to_dashboard(dashboard, callback_url)
        return AccountResult(account, ResultCode.SUCCESS)
    except asyncio.CancelledError:
        return AccountResult(account, ResultCode.CANCELLED, "đã dừng theo yêu cầu")
    except FlowStopped as error:
        return AccountResult(account, error.code, str(error))
    except Exception as error:
        # Chỉ báo tên loại lỗi để không lộ mật khẩu, OTP hay response body.
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
