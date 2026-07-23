from __future__ import annotations

import importlib.util
import unittest

if importlib.util.find_spec("playwright"):
    from playwright.async_api import async_playwright

    from login_codex_9router.accounts import Account
    from login_codex_9router.auth.automation import FlowStopped, ResultCode, _complete_openai_login
    from login_codex_9router.cancellation import CancellationToken


@unittest.skipUnless(importlib.util.find_spec("playwright"), "playwright chưa được cài")
class OpenAIErrorFlowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.playwright = await async_playwright().start()
        try:
            self.browser = await self.playwright.chromium.launch(channel="chrome", headless=True)
        except Exception as error:
            await self.playwright.stop()
            self.skipTest(f"Chrome không khả dụng: {type(error).__name__}")
        self.page = await self.browser.new_page()
        self.account = Account(1, "user@example.com", "wrong", "JBSWY3DPEHPK3PXP")

    async def asyncTearDown(self) -> None:
        if hasattr(self, "browser"):
            await self.browser.close()
            await self.playwright.stop()

    async def _run_error(self, field: str, message: str) -> ResultCode:
        input_html = {
            "password": '<label>Password<input type="password"></label>',
            "otp": '<label>Verification code<input autocomplete="one-time-code"></label>',
        }[field]
        await self.page.set_content(
            input_html
            + '<button type="submit" onclick="submitCount++; alertBox.textContent=message">Continue</button>'
            + '<p id="alertBox" role="alert"></p>'
            + f"<script>let submitCount=0;const message={message!r}</script>"
        )
        with self.assertRaises(FlowStopped) as raised:
            await _complete_openai_login(self.page, self.account, CancellationToken())
        self.submit_count = await self.page.evaluate("submitCount")
        return raised.exception.code

    async def test_invalid_password_stops_after_one_submit(self) -> None:
        code = await self._run_error("password", "Incorrect password")
        self.assertEqual(code, ResultCode.INVALID_PASSWORD)
        self.assertEqual(self.submit_count, 1)

    async def test_invalid_otp_stops_after_one_submit(self) -> None:
        code = await self._run_error("otp", "Incorrect verification code")
        self.assertEqual(code, ResultCode.INVALID_OTP)
        self.assertEqual(self.submit_count, 1)


if __name__ == "__main__":
    unittest.main()
