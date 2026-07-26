"""Mã trạng thái và kiểu kết quả dùng chung cho toàn bộ luồng đăng nhập."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from ..accounts import Account

DEFAULT_CALLBACK_PORT = 1455

# Trạng thái tạm thời khi đang chờ người dùng tự xử lý CAPTCHA / xác minh điện thoại.
# Không phải kết quả cuối nên không nằm trong ResultCode.
WAITING_MANUAL_STATUS = "waiting_manual"

# Thời gian chờ mặc định cho một bước xác minh thủ công.
MANUAL_VERIFICATION_TIMEOUT = 300

# (status, detail) — báo tiến độ giữa chừng lên UI.
ProgressCallback = Callable[[str, str], None]


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
    """Dừng luồng của một tài khoản kèm mã trạng thái để báo lên UI."""

    def __init__(self, code: ResultCode, detail: str) -> None:
        super().__init__(detail)
        self.code = code
