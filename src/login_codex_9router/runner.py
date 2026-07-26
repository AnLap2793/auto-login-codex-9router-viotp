import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .accounts import Account, parse_accounts
from .auth.results import DEFAULT_CALLBACK_PORT, MANUAL_VERIFICATION_TIMEOUT
from .cancellation import CancellationToken
from .config import normalize_host

if TYPE_CHECKING:
    from .auth.automation import AccountResult


class CallbackPortBusyError(RuntimeError):
    """Không giữ được cổng callback OAuth nên không tài khoản nào chạy được."""


@dataclass(frozen=True, slots=True)
class StatusUpdate:
    line_number: int
    masked_email: str
    status: str
    detail: str = ""


StatusCallback = Callable[[StatusUpdate], None]

# (line_number, token riêng của tài khoản) — để UI bỏ qua từng tài khoản.
AccountStartCallback = Callable[[int, CancellationToken], None]


def _emit(callback: StatusCallback | None, update: StatusUpdate) -> None:
    if callback:
        callback(update)


async def run_text(
    text: str,
    host: str,
    on_status: StatusCallback | None = None,
    cancellation: CancellationToken | None = None,
    dashboard_password: str | None = None,
    headless: bool = False,
    callback_port: int = DEFAULT_CALLBACK_PORT,
    manual_timeout: float | None = None,
    on_account_start: AccountStartCallback | None = None,
) -> list["AccountResult"]:
    """`callback_port` chỉ để test dùng `0` (OS tự cấp cổng) cho khỏi phụ thuộc cổng cố định.
    Chạy thật phải giữ 1455 vì OpenAI chỉ chấp nhận redirect_uri ở cổng đó.

    `manual_timeout` là số giây chờ người dùng tự xử lý CAPTCHA / xác minh điện thoại trong
    cửa sổ Chrome. Mặc định: bật ở chế độ hiển thị, tắt khi `headless` vì không có cửa sổ
    để thao tác. Đặt `0` để luôn dừng ngay như trước.

    `on_account_start(line_number, token)` trả về token riêng của từng tài khoản để UI có thể
    bỏ qua một tài khoản mà không dừng các tài khoản còn lại.
    """
    host = normalize_host(host)
    cancellation = cancellation or CancellationToken()
    accounts, errors = parse_accounts(text)
    for error in errors:
        _emit(on_status, StatusUpdate(error.line_number, "—", "failed", error.message))
    for account in accounts:
        _emit(on_status, StatusUpdate(account.line_number, account.masked_email, "pending"))
    if not accounts:
        return []

    # Chạy ẩn thì không có cửa sổ để người dùng thao tác, nên không chờ dù cấu hình bao nhiêu.
    if headless:
        wait_seconds = 0.0
    else:
        wait_seconds = MANUAL_VERIFICATION_TIMEOUT if manual_timeout is None else max(0.0, manual_timeout)

    from playwright.async_api import async_playwright

    from .auth.automation import AccountResult, ResultCode, run_account
    from .integrations.oauth_callback import CallbackServer

    async def run_one(account: Account) -> AccountResult:
        if cancellation.cancelled:
            result = AccountResult(account, ResultCode.CANCELLED, "đã dừng theo yêu cầu")
        else:
            account_token = cancellation.child()
            if on_account_start:
                on_account_start(account.line_number, account_token)
            _emit(on_status, StatusUpdate(account.line_number, account.masked_email, "running"))

            def report(status: str, detail: str) -> None:
                _emit(on_status, StatusUpdate(account.line_number, account.masked_email, status, detail))

            result = await run_account(
                playwright,
                account,
                host,
                callback_server,
                account_token,
                dashboard_password,
                headless,
                wait_seconds,
                report,
            )
        _emit(on_status, StatusUpdate(account.line_number, account.masked_email, result.code, result.detail))
        return result

    try:
        callback_server = CallbackServer(port=callback_port)
    except OSError as error:
        # Cổng 1455 do OpenAI quy định cho redirect_uri của Codex; không thể đổi sang cổng khác.
        raise CallbackPortBusyError(
            f"Cổng {callback_port} đang bị chiếm nên không nhận được callback OAuth. "
            "Đóng ứng dụng này nếu đang mở bản khác, hoặc thoát Codex CLI, rồi thử lại."
        ) from error

    try:
        with callback_server:
            async with async_playwright() as playwright:
                tasks = [asyncio.create_task(run_one(account)) for account in accounts]
                while not all(task.done() for task in tasks):
                    if cancellation.cancelled:
                        for task in tasks:
                            if not task.done():
                                task.cancel()
                        break
                    await asyncio.sleep(0.1)
                results = await asyncio.gather(*tasks, return_exceptions=True)
    except BaseException:
        # `__enter__` hỏng (ví dụ không tạo được thread) thì `__exit__` không chạy,
        # socket vẫn giữ cổng 1455 tới hết đời tiến trình và ứng dụng tự chặn chính mình.
        callback_server.close_if_idle()
        raise

    finalized: list[AccountResult] = []
    for account, result in zip(accounts, results, strict=True):
        if isinstance(result, BaseException):
            result = AccountResult(account, ResultCode.CANCELLED, "đã dừng theo yêu cầu")
            _emit(on_status, StatusUpdate(account.line_number, account.masked_email, result.code, result.detail))
        finalized.append(result)
    return finalized
