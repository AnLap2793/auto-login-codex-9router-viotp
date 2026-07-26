"""Xin OAuth URL từ 9router và kiểm tra tham số trả về ở callback."""

import asyncio
import json
import urllib.parse
import urllib.request
from urllib.parse import parse_qs, urlsplit

from playwright.async_api import BrowserContext, Page

from .results import DEFAULT_CALLBACK_PORT, FlowStopped, ResultCode

AUTHORIZE_TIMEOUT_SECONDS = 15


async def open_oauth(
    context: BrowserContext, host: str, callback_port: int = DEFAULT_CALLBACK_PORT
) -> tuple[Page, str]:
    """Gọi API authorize của 9router bằng cookie của context, rồi mở OAuth URL trong tab mới."""
    redirect_uri = f"http://localhost:{callback_port}/auth/callback"

    def _request_authorize(cookie_header: str) -> bytes:
        query = urllib.parse.urlencode({"redirect_uri": redirect_uri})
        request = urllib.request.Request(f"{host}/api/oauth/codex/authorize?{query}")
        if cookie_header:
            request.add_header("Cookie", cookie_header)
        with urllib.request.urlopen(request, timeout=AUTHORIZE_TIMEOUT_SECONDS) as response:
            return response.read()

    try:
        cookies = await context.cookies(host)
        cookie_header = "; ".join(f"{c['name']}={c['value']}" for c in cookies) if cookies else ""
        payload = await asyncio.to_thread(_request_authorize, cookie_header)
        auth_data = json.loads(payload.decode())
    except Exception as error:
        raise FlowStopped(ResultCode.FAILED, f"không thể kết nối API 9router: {type(error).__name__}") from error

    auth_url = auth_data.get("authUrl") if isinstance(auth_data, dict) else None
    state = auth_data.get("state") if isinstance(auth_data, dict) else None
    if not isinstance(auth_url, str) or not isinstance(state, str) or not auth_url or not state:
        raise FlowStopped(ResultCode.FAILED, "9router không trả về OAuth URL hoặc state")

    oauth_page = await context.new_page()
    await oauth_page.goto(auth_url, wait_until="domcontentloaded")
    return oauth_page, state


def verify_callback(callback_url: str) -> None:
    """Chỉ chấp nhận callback có mã ủy quyền; không log giá trị mã."""
    params = parse_qs(urlsplit(callback_url).query)
    if params.get("error"):
        description = params.get("error_description", ["OAuth error"])[0]
        raise FlowStopped(ResultCode.FAILED, f"OpenAI từ chối ủy quyền: {description}")
    if not params.get("code"):
        raise FlowStopped(ResultCode.FAILED, "callback thiếu mã ủy quyền OAuth")
