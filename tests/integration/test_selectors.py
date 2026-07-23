import importlib.util
import unittest

if importlib.util.find_spec("playwright"):
    from playwright.async_api import async_playwright

    from login_codex_9router.auth.selectors import (
        blocker,
        email_input,
        otp_input,
        password_input,
        visible_error_text,
    )


@unittest.skipUnless(importlib.util.find_spec("playwright"), "playwright chưa được cài")
class SelectorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.playwright = await async_playwright().start()
        try:
            self.browser = await self.playwright.chromium.launch(channel="chrome", headless=True)
        except Exception as error:
            await self.playwright.stop()
            self.skipTest(f"Chrome không khả dụng: {type(error).__name__}")
        self.page = await self.browser.new_page()

    async def asyncTearDown(self) -> None:
        if hasattr(self, "browser"):
            await self.browser.close()
            await self.playwright.stop()

    async def test_finds_semantic_login_fields(self) -> None:
        await self.page.set_content(
            '<label>Email address<input type="email"></label>'
            '<label>Password<input type="password"></label>'
            '<label>Verification code<input autocomplete="one-time-code"></label>'
        )
        self.assertIsNotNone(await email_input(self.page))
        self.assertIsNotNone(await password_input(self.page))
        self.assertIsNotNone(await otp_input(self.page))

    async def test_detects_phone_and_captcha(self) -> None:
        await self.page.set_content('<label>Phone<input type="tel"></label>')
        self.assertEqual(await blocker(self.page), "phone")
        await self.page.set_content("<p>Verify you are human</p>")
        self.assertEqual(await blocker(self.page), "captcha")

    async def test_reads_only_visible_bounded_alerts(self) -> None:
        await self.page.set_content(
            '<p role="alert">Incorrect password</p>'
            '<p role="alert" style="display:none">secret hidden error</p>'
            '<p aria-live="polite">Try again later</p>'
        )
        text = await visible_error_text(self.page)
        self.assertIn("Incorrect password", text)
        self.assertIn("Try again later", text)
        self.assertNotIn("secret hidden error", text)


if __name__ == "__main__":
    unittest.main()
