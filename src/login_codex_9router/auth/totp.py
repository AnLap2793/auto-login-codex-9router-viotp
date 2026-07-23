import asyncio
import base64
import binascii
import hashlib
import hmac
import struct
import time


class TwoFactorError(RuntimeError):
    pass


def _decode_secret(secret: str) -> bytes:
    normalized = "".join(secret.split()).replace("-", "").upper()
    if not normalized:
        raise TwoFactorError("khóa 2FA trống")
    padded = normalized + "=" * (-len(normalized) % 8)
    try:
        return base64.b32decode(padded, casefold=True)
    except (binascii.Error, ValueError) as error:
        raise TwoFactorError("khóa 2FA không phải Base32 hợp lệ") from error


def generate_totp(secret: str, timestamp: float | None = None, digits: int = 6) -> str:
    if digits < 6 or digits > 8:
        raise ValueError("digits phải từ 6 đến 8")
    counter = int(time.time() if timestamp is None else timestamp) // 30
    digest = hmac.new(_decode_secret(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % (10**digits)
    return f"{code:0{digits}d}"


async def fetch_token(
    secret: str, minimum_validity: float = 5, next_window: bool = False
) -> str:
    remaining = 30 - time.time() % 30
    if next_window or remaining < minimum_validity:
        await asyncio.sleep(remaining + 0.1)
    return generate_totp(secret)
