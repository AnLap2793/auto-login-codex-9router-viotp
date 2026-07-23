import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_BASE_URL = "https://api.viotp.com"
DEFAULT_TIMEOUT = 10


class ViotpError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Service:
    id: int
    name: str
    price: int


@dataclass(frozen=True, slots=True)
class Network:
    id: int
    name: str


OPENAI_SERVICE = Service(1234, "OpenAI | ChatGPT", 2900)


def _get(path: str, token: str, base_url: str, timeout: float) -> object:
    token = token.strip()
    if not token:
        raise ViotpError("token VIOTP trống")
    url = f"{base_url.rstrip('/')}{path}?{urlencode({'token': token})}"
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "login-codex-9router/0.1"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as error:
        raise ViotpError(f"VIOTP trả về HTTP {error.code}") from error
    except (URLError, TimeoutError, OSError) as error:
        raise ViotpError("không thể kết nối VIOTP") from error
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ViotpError("VIOTP trả về dữ liệu không hợp lệ") from error

    if not isinstance(payload, dict):
        raise ViotpError("VIOTP trả về dữ liệu không hợp lệ")
    if payload.get("status_code") != 200 or payload.get("success") is not True:
        message = payload.get("message")
        if payload.get("status_code") == 401:
            raise ViotpError("token VIOTP không hợp lệ")
        if isinstance(message, str) and message:
            raise ViotpError(message.replace(token, "***"))
        raise ViotpError("VIOTP từ chối yêu cầu")
    return payload.get("data")


def get_balance(
    token: str, *, base_url: str = API_BASE_URL, timeout: float = DEFAULT_TIMEOUT
) -> int | float:
    data = _get("/users/balance", token, base_url, timeout)
    if not isinstance(data, dict) or not isinstance(data.get("balance"), (int, float)):
        raise ViotpError("VIOTP không trả về số dư hợp lệ")
    return data["balance"]


def get_networks(
    token: str, *, base_url: str = API_BASE_URL, timeout: float = DEFAULT_TIMEOUT
) -> list[Network]:
    data = _get("/networks/get", token, base_url, timeout)
    if not isinstance(data, list):
        raise ViotpError("VIOTP không trả về danh sách nhà mạng hợp lệ")
    networks: list[Network] = []
    for item in data:
        if not isinstance(item, dict) or not isinstance(item.get("id"), int) or not isinstance(item.get("name"), str):
            raise ViotpError("VIOTP không trả về danh sách nhà mạng hợp lệ")
        networks.append(Network(item["id"], item["name"]))
    return networks
