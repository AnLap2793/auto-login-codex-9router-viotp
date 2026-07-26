"""Luồng đăng nhập OpenAI: email, mật khẩu, TOTP và phát hiện bước chặn thủ công."""

import asyncio
import re

from playwright.async_api import Page

from ..accounts import Account
from ..cancellation import CancellationToken
from .errors import AuthErrorCode, MESSAGES, classify_text
from .response_observer import ResponseObserver
from .results import (
    DEFAULT_CALLBACK_PORT,
    WAITING_MANUAL_STATUS,
    FlowStopped,
    ProgressCallback,
    ResultCode,
)
from .selectors import blocker, email_input, first_visible, otp_input, password_input, visible_error_text
from .totp import fetch_token

# Thời gian tối đa cho toàn bộ luồng đăng nhập của một tài khoản.
LOGIN_TIMEOUT_SECONDS = 300


async def _click_continue(page: Page) -> None:
    button = await first_visible(
        page.get_by_role("button", name=re.compile(r"^(continue|next|submit|verify)$", re.I)),
        page.locator('button[type="submit"]'),
    )
    if not button:
        raise FlowStopped(ResultCode.FAILED, "không tìm thấy nút tiếp tục")
    await button.click()


def _raise_auth_error(code: AuthErrorCode) -> None:
    raise FlowStopped(ResultCode(code.value), MESSAGES[code])


async def _auth_error(page: Page, observer: ResponseObserver) -> AuthErrorCode | None:
    ui_error = classify_text(await visible_error_text(page))
    if ui_error:
        return ui_error
    signal = observer.latest()
    return signal.code if signal else None


async def _wait_after_submit(
    page: Page,
    observer: ResponseObserver,
    token: CancellationToken,
    callback_prefix: str,
    timeout: float = 2,
) -> AuthErrorCode | None:
    """Theo dõi lỗi UI/HTTP ngay sau khi submit; dừng sớm khi đã tới callback OAuth."""
    deadline = asyncio.get_running_loop().time() + timeout
    try:
        while asyncio.get_running_loop().time() < deadline:
            token.raise_if_cancelled()
            error = await _auth_error(page, observer)
            if error:
                return error
            if page.url.startswith(callback_prefix):
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
    callback_prefix: str,
) -> None:
    """Nhập TOTP. Chỉ retry đúng một lần và chỉ khi mã hết hạn."""
    for attempt in range(2):
        otp = await otp_input(page, timeout=2_000)
        if not otp:
            return
        await otp.fill(await fetch_token(account.two_factor_secret, next_window=attempt > 0))
        observer.start_step()
        await _click_continue(page)
        error = await _wait_after_submit(page, observer, token, callback_prefix)
        if error == AuthErrorCode.EXPIRED_OTP and attempt == 0:
            continue
        if error:
            _raise_auth_error(error)
        return


_BLOCKER_LABELS = {
    "phone": ("xác minh số điện thoại", ResultCode.PHONE_VERIFICATION_REQUIRED),
    "captcha": ("CAPTCHA", ResultCode.CAPTCHA_REQUIRED),
}


async def _wait_for_manual_resolution(
    page: Page,
    blocked: str,
    token: CancellationToken,
    timeout: float,
    callback_prefix: str,
    on_progress: ProgressCallback | None,
) -> bool:
    """Chờ người dùng tự xử lý bước chặn ngay trong cửa sổ Chrome đang mở.

    Ứng dụng không tự điền gì ở đây — người dùng nhập số của họ và mã xác minh bằng tay.
    Trả về True nếu bước chặn đã qua trước khi hết giờ.
    """
    label = _BLOCKER_LABELS[blocked][0]
    deadline = asyncio.get_running_loop().time() + timeout
    if on_progress:
        minutes = max(1, round(timeout / 60))
        on_progress(
            WAITING_MANUAL_STATUS,
            f"đang chờ bạn {label} trong cửa sổ Chrome (tối đa {minutes} phút)",
        )
    while asyncio.get_running_loop().time() < deadline:
        token.raise_if_cancelled()
        if page.url.startswith(callback_prefix):
            return True
        try:
            if await blocker(page) is None:
                return True
        except Exception:
            # Trang đang điều hướng giữa chừng: coi như chưa xong, thử lại vòng sau.
            pass
        await page.wait_for_timeout(1000)
    return False


async def complete_openai_login(
    page: Page,
    account: Account,
    token: CancellationToken,
    callback_port: int = DEFAULT_CALLBACK_PORT,
    manual_timeout: float = 0,
    on_progress: ProgressCallback | None = None,
) -> None:
    """Điền lần lượt email → mật khẩu → OTP cho tới khi OpenAI chuyển sang callback OAuth."""
    callback_prefix = f"http://localhost:{callback_port}/"
    observer = ResponseObserver(page)
    deadline = asyncio.get_running_loop().time() + LOGIN_TIMEOUT_SECONDS
    email_done = password_done = otp_done = False
    while asyncio.get_running_loop().time() < deadline:
        token.raise_if_cancelled()
        if page.url.startswith(callback_prefix):
            return
        error = classify_text(await visible_error_text(page))
        if error:
            _raise_auth_error(error)
        blocked = await blocker(page)
        if blocked:
            label, code = _BLOCKER_LABELS[blocked]
            if manual_timeout > 0:
                started = asyncio.get_running_loop().time()
                resolved = await _wait_for_manual_resolution(
                    page, blocked, token, manual_timeout, callback_prefix, on_progress
                )
                # Thời gian người dùng thao tác không tính vào hạn đăng nhập.
                deadline += asyncio.get_running_loop().time() - started
                if resolved:
                    if on_progress:
                        on_progress("running", f"đã qua bước {label}, đang chạy tiếp")
                    continue
                raise FlowStopped(code, f"hết thời gian chờ bạn {label}")
            raise FlowStopped(code, f"cần {label} thủ công")

        email = await email_input(page, timeout=700)
        if email and not email_done:
            await email.click()
            await email.fill("")
            # Gõ từng ký tự vì form OpenAI xác thực theo sự kiện bàn phím.
            await email.type(account.email, delay=30)
            await page.wait_for_timeout(1000)
            observer.start_step()
            await _click_continue(page)
            error = await _wait_after_submit(page, observer, token, callback_prefix)
            if error:
                _raise_auth_error(error)
            email_done = True
            continue
        password = await password_input(page, timeout=700)
        if password and not password_done:
            await password.fill(account.password)
            observer.start_step()
            await _click_continue(page)
            error = await _wait_after_submit(page, observer, token, callback_prefix)
            if error:
                _raise_auth_error(error)
            password_done = True
            continue
        if await otp_input(page, timeout=700) and not otp_done:
            await _submit_otp(page, account, token, observer, callback_prefix)
            otp_done = True
            continue
        await page.wait_for_timeout(500)
    raise FlowStopped(ResultCode.FAILED, "hết thời gian đăng nhập OpenAI")
