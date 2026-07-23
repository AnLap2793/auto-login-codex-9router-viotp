from urllib.parse import urlsplit


def normalize_host(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("HOST phải là URL HTTP/HTTPS hợp lệ")
    return f"{parsed.scheme}://{parsed.netloc}"
