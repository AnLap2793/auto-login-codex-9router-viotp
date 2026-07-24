"""E2E live test — chạy toàn bộ luồng OAuth với 9router và OpenAI thật.

Yêu cầu environment variables:
    E2E_NINE_ROUTER_HOST    — URL 9router, ví dụ http://localhost:20127
    E2E_OPENAI_EMAIL        — Email tài khoản OpenAI thử nghiệm
    E2E_OPENAI_PASSWORD     — Mật khẩu tài khoản
    E2E_OPENAI_TOTP_SECRET  — Base32 TOTP secret (2FA)
    E2E_DASHBOARD_PASSWORD  — Mật khẩu dashboard 9router (tùy chọn)

Skip toàn bộ nếu thiếu biến bắt buộc.
"""

from __future__ import annotations

import importlib.util
import os
import unittest

_REQUIRED_ENV = (
    "E2E_NINE_ROUTER_HOST",
    "E2E_OPENAI_EMAIL",
    "E2E_OPENAI_PASSWORD",
    "E2E_OPENAI_TOTP_SECRET",
)

_SKIP_REASON = "thiếu E2E environment variables: " + ", ".join(_REQUIRED_ENV)


def _env_ready() -> bool:
    return all(os.environ.get(key) for key in _REQUIRED_ENV)


@unittest.skipUnless(_env_ready(), _SKIP_REASON)
@unittest.skipUnless(importlib.util.find_spec("playwright"), "playwright chưa được cài")
class LiveE2ETests(unittest.IsolatedAsyncioTestCase):
    """Chạy luồng thật: dashboard → OAuth → login → MFA → callback → Connect."""

    async def asyncSetUp(self) -> None:
        from playwright.async_api import async_playwright

        from login_codex_9router.accounts import Account
        from login_codex_9router.auth.automation import run_account
        from login_codex_9router.cancellation import CancellationToken
        from login_codex_9router.integrations.oauth_callback import CallbackServer

        self.host = os.environ["E2E_NINE_ROUTER_HOST"]
        self.dashboard_password = os.environ.get("E2E_DASHBOARD_PASSWORD")
        self.account = Account(
            line_number=1,
            email=os.environ["E2E_OPENAI_EMAIL"],
            password=os.environ["E2E_OPENAI_PASSWORD"],
            two_factor_secret=os.environ["E2E_OPENAI_TOTP_SECRET"],
        )
        self.token = CancellationToken()

        self.playwright = await async_playwright().start()
        try:
            self.browser = await self.playwright.chromium.launch(
                channel="chrome", headless=False
            )
        except Exception as error:
            await self.playwright.stop()
            self.skipTest(f"Chrome không khả dụng: {type(error).__name__}")

        self.callback_server = CallbackServer()
        self.callback_server.__enter__()

        # Lưu references cho tearDown
        self._run_account = run_account
        self._CallbackServer = CallbackServer

    async def asyncTearDown(self) -> None:
        if hasattr(self, "callback_server"):
            self.callback_server.__exit__(None, None, None)
        if hasattr(self, "browser"):
            await self.browser.close()
            await self.playwright.stop()

    async def test_full_oauth_flow_success(self) -> None:
        """Dashboard login → OAuth popup → email/password → MFA → callback → Connect."""
        result = await self._run_account(
            self.playwright,
            self.account,
            self.host,
            self.callback_server,
            self.token,
            dashboard_password=self.dashboard_password,
            headless=False,
        )
        self.assertEqual(
            result.code,
            "success",
            f"E2E flow thất bại: {result.code} — {result.detail}",
        )


if __name__ == "__main__":
    unittest.main()
