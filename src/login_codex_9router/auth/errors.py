from dataclasses import dataclass
from enum import StrEnum


class AuthErrorCode(StrEnum):
    INVALID_EMAIL = "invalid_email"
    INVALID_PASSWORD = "invalid_password"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_DISABLED = "account_disabled"
    RATE_LIMITED = "rate_limited"
    INVALID_OTP = "invalid_otp"
    EXPIRED_OTP = "expired_otp"
    LOGIN_REJECTED = "login_rejected"


MESSAGES = {
    AuthErrorCode.INVALID_EMAIL: "email hoặc tài khoản không tồn tại",
    AuthErrorCode.INVALID_PASSWORD: "mật khẩu OpenAI không đúng",
    AuthErrorCode.ACCOUNT_LOCKED: "tài khoản OpenAI bị khóa hoặc tạm ngưng",
    AuthErrorCode.ACCOUNT_DISABLED: "tài khoản OpenAI đã bị vô hiệu hóa",
    AuthErrorCode.RATE_LIMITED: "OpenAI đang giới hạn yêu cầu; không tự động thử lại",
    AuthErrorCode.INVALID_OTP: "mã xác thực không đúng; kiểm tra khóa 2FA",
    AuthErrorCode.EXPIRED_OTP: "mã xác thực đã hết hạn",
    AuthErrorCode.LOGIN_REJECTED: "OpenAI từ chối đăng nhập",
}


@dataclass(frozen=True, slots=True)
class AuthSignal:
    code: AuthErrorCode
    status: int | None = None


_PATTERNS = (
    (AuthErrorCode.RATE_LIMITED, ("too many attempts", "too many requests", "try again later", "rate limit")),
    (AuthErrorCode.ACCOUNT_DISABLED, ("deactivated", "disabled", "deleted account")),
    (AuthErrorCode.ACCOUNT_LOCKED, ("account is locked", "account locked", "suspended")),
    (AuthErrorCode.EXPIRED_OTP, ("code has expired", "expired code", "verification code expired")),
    (
        AuthErrorCode.INVALID_OTP,
        (
            "incorrect verification code",
            "invalid verification code",
            "invalid authentication code",
            "incorrect authentication code",
            "invalid otp",
            "incorrect otp",
            "invalid code",
        ),
    ),
    (AuthErrorCode.INVALID_PASSWORD, ("incorrect password", "invalid password", "wrong password")),
    (AuthErrorCode.INVALID_EMAIL, ("account not found", "email not found", "user not found", "couldn't find")),
)


def classify_text(text: str) -> AuthErrorCode | None:
    normalized = " ".join(text.lower().split())
    for code, phrases in _PATTERNS:
        if any(phrase in normalized for phrase in phrases):
            return code
    return None


def classify_response(status: int, codes: tuple[str, ...] = ()) -> AuthSignal | None:
    for value in codes:
        classified = classify_text(value.replace("_", " ").replace("-", " "))
        if classified:
            return AuthSignal(classified, status)
    if status == 429:
        return AuthSignal(AuthErrorCode.RATE_LIMITED, status)
    if status in {401, 403}:
        return AuthSignal(AuthErrorCode.LOGIN_REJECTED, status)
    return None
