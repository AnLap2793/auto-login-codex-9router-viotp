"""Đăng nhập dashboard 9router bằng mật khẩu (bỏ qua nếu dashboard không bật)."""

import re
from urllib.parse import urlsplit

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from ..cancellation import CancellationToken
from .results import FlowStopped, ResultCode
from .selectors import password_input


def url_path(url: str) -> str:
    return urlsplit(url).path.rstrip("/") or "/"


async def login_dashboard(page: Page, password: str | None, token: CancellationToken) -> None:
    if url_path(page.url) != "/login":
        return
    if not password:
        raise FlowStopped(ResultCode.DASHBOARD_AUTH_REQUIRED, "cần mật khẩu dashboard 9router")
    token.raise_if_cancelled()
    password_field = await password_input(page, timeout=10_000)
    if not password_field:
        raise FlowStopped(ResultCode.DASHBOARD_AUTH_FAILED, "9router không hỗ trợ đăng nhập mật khẩu")
    await password_field.fill(password)
    await page.get_by_role("button", name="Login", exact=True).click()
    try:
        await page.wait_for_url(re.compile(r"/dashboard(?:/|$)"), timeout=15_000)
    except PlaywrightTimeoutError as error:
        body = (await page.locator("body").inner_text()).lower()
        detail = "dashboard bị khóa tạm thời" if "locked" in body else "mật khẩu dashboard không đúng"
        raise FlowStopped(ResultCode.DASHBOARD_AUTH_FAILED, detail) from error
