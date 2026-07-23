import base64
import ctypes
import json
import os
import tempfile
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA_VERSION = 1
DEFAULT_HOST = "http://localhost:20127"
DEFAULT_NETWORK = "Tất cả nhà mạng"
_BROWSER_MODES = {"visible", "headless"}


@dataclass(frozen=True, slots=True)
class AppConfig:
    host: str = DEFAULT_HOST
    browser_mode: str = "visible"
    dashboard_password: str = ""
    viotp_token: str = ""
    viotp_network: str = DEFAULT_NETWORK


DEFAULT_CONFIG = AppConfig()


class ConfigError(ValueError):
    pass


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def normalize_host(value: str) -> str:
    parsed = urlsplit(value.strip())
    try:
        parsed.port
    except ValueError as error:
        raise ValueError("HOST phải là URL HTTP/HTTPS hợp lệ") from error
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or "\\" in parsed.netloc
        or any(character.isspace() for character in parsed.netloc)
    ):
        raise ValueError("HOST phải là URL HTTP/HTTPS hợp lệ")
    return f"{parsed.scheme}://{parsed.netloc}"


def get_config_path(local_app_data: Path | None = None) -> Path:
    base = local_app_data
    if base is None:
        value = os.environ.get("LOCALAPPDATA")
        base = Path(value) if value else Path.home() / "AppData" / "Local"
    return base / "login-codex-9router" / "config.json"


def _dpapi(function_name: str, data: bytes) -> bytes:
    if os.name != "nt":
        raise ConfigError("Windows DPAPI không khả dụng trên hệ điều hành này")
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    function = getattr(crypt32, function_name)
    function.argtypes = [
        ctypes.POINTER(_DataBlob),
        wintypes.LPCWSTR,
        ctypes.POINTER(_DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    function.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p

    buffer = ctypes.create_string_buffer(data)
    source = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = _DataBlob()
    if not function(ctypes.byref(source), None, None, None, None, 0x01, ctypes.byref(output)):
        raise ConfigError(f"Windows DPAPI thất bại (mã {ctypes.get_last_error()})")
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        kernel32.LocalFree(output.pbData)


def _protect_secret(value: str) -> str | None:
    if not value:
        return None
    return base64.b64encode(_dpapi("CryptProtectData", value.encode("utf-8"))).decode("ascii")


def _unprotect_secret(value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str) or not value:
        raise ConfigError("Dữ liệu bí mật không hợp lệ")
    try:
        encrypted = base64.b64decode(value, validate=True)
        return _dpapi("CryptUnprotectData", encrypted).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as error:
        raise ConfigError("Dữ liệu bí mật không hợp lệ") from error


def _validate(config: AppConfig) -> AppConfig:
    if not all(
        isinstance(value, str)
        for value in (
            config.host,
            config.browser_mode,
            config.dashboard_password,
            config.viotp_token,
            config.viotp_network,
        )
    ):
        raise ConfigError("Kiểu dữ liệu cấu hình không hợp lệ")
    try:
        host = normalize_host(config.host)
    except ValueError as error:
        raise ConfigError(str(error)) from error
    if config.browser_mode not in _BROWSER_MODES:
        raise ConfigError("Chế độ Chrome không hợp lệ")
    network = config.viotp_network.strip()
    if not network:
        raise ConfigError("Nhà mạng VIOTP không hợp lệ")
    if not config.viotp_token and network != DEFAULT_NETWORK:
        raise ConfigError("Không thể lưu nhà mạng khi chưa có token VIOTP")
    return AppConfig(host, config.browser_mode, config.dashboard_password, config.viotp_token, network)


def _encode(config: AppConfig) -> dict[str, object]:
    return {
        "version": SCHEMA_VERSION,
        "host": config.host,
        "browser_mode": config.browser_mode,
        "dashboard_password_dpapi": _protect_secret(config.dashboard_password),
        "viotp": {
            "token_dpapi": _protect_secret(config.viotp_token),
            "network": config.viotp_network,
        },
    }


def _decode(payload: object) -> AppConfig:
    if not isinstance(payload, dict) or set(payload) != {
        "version",
        "host",
        "browser_mode",
        "dashboard_password_dpapi",
        "viotp",
    }:
        raise ConfigError("Cấu trúc file cấu hình không hợp lệ")
    if type(payload["version"]) is not int or payload["version"] != SCHEMA_VERSION:
        raise ConfigError("Phiên bản file cấu hình không được hỗ trợ")
    viotp = payload["viotp"]
    if not isinstance(viotp, dict) or set(viotp) != {"token_dpapi", "network"}:
        raise ConfigError("Cấu hình VIOTP không hợp lệ")
    return _validate(
        AppConfig(
            host=payload["host"],
            browser_mode=payload["browser_mode"],
            dashboard_password=_unprotect_secret(payload["dashboard_password_dpapi"]),
            viotp_token=_unprotect_secret(viotp["token_dpapi"]),
            viotp_network=viotp["network"],
        )
    )


def load_config(path: Path | None = None) -> tuple[AppConfig, str | None]:
    path = path or get_config_path()
    if not path.exists():
        return DEFAULT_CONFIG, None
    try:
        with path.open(encoding="utf-8") as file:
            return _decode(json.load(file)), None
    except (ConfigError, json.JSONDecodeError, OSError, TypeError, UnicodeError) as error:
        return DEFAULT_CONFIG, str(error) or type(error).__name__


def save_config(config: AppConfig, path: Path | None = None) -> AppConfig:
    path = path or get_config_path()
    normalized = _validate(config)
    payload = _encode(normalized)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as file:
            temporary_path = Path(file.name)
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path:
            temporary_path.unlink(missing_ok=True)
    return normalized
