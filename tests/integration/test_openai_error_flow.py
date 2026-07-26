from __future__ import annotations

import importlib.util
import unittest

if importlib.util.find_spec("playwright"):
    from playwright.async_api import async_playwright

    from login_codex_9router.accounts import Account
    from login_codex_9router.auth.automation import FlowStopped, ResultCode, _complete_openai_login
    from login_codex_9router.auth.openai_login import _submit_otp
    from login_codex_9router.auth.response_observer import ResponseObserver
    from login_codex_9router.cancellation import CancellationToken

OTP_FIELD = '<label>Verification code<input autocomplete="one-time-code"></label>'
PASSWORD_FIELD = '<label>Password<input type="password"></label>'
EMAIL_FIELD = '<label>Email<input type="email" name="username"></label>'


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
        input_html = {"password": PASSWORD_FIELD, "otp": OTP_FIELD, "email": EMAIL_FIELD}[field]
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

    async def test_invalid_email_stops_immediately(self) -> None:
        code = await self._run_error("email", "We couldn't find your account")
        self.assertEqual(code, ResultCode.INVALID_EMAIL)
        self.assertEqual(self.submit_count, 1)

    async def test_account_locked_stops_immediately(self) -> None:
        code = await self._run_error("password", "Your account is locked")
        self.assertEqual(code, ResultCode.ACCOUNT_LOCKED)
        self.assertEqual(self.submit_count, 1)

    async def test_account_disabled_stops_immediately(self) -> None:
        code = await self._run_error("password", "This account has been deactivated")
        self.assertEqual(code, ResultCode.ACCOUNT_DISABLED)
        self.assertEqual(self.submit_count, 1)

    async def test_rate_limited_stops_without_retry(self) -> None:
        code = await self._run_error("password", "Too many attempts, try again later")
        self.assertEqual(code, ResultCode.RATE_LIMITED)
        self.assertEqual(self.submit_count, 1)


@unittest.skipUnless(importlib.util.find_spec("playwright"), "playwright chưa được cài")
class ExpiredOtpRetryTests(unittest.IsolatedAsyncioTestCase):
    """`expired_otp` là lỗi duy nhất được retry, và chỉ đúng một lần."""

    async def asyncSetUp(self) -> None:
        self.playwright = await async_playwright().start()
        try:
            self.browser = await self.playwright.chromium.launch(channel="chrome", headless=True)
        except Exception as error:
            await self.playwright.stop()
            self.skipTest(f"Chrome không khả dụng: {type(error).__name__}")
        self.page = await self.browser.new_page()
        self.account = Account(1, "user@example.com", "pw", "JBSWY3DPEHPK3PXP")

    async def asyncTearDown(self) -> None:
        if hasattr(self, "browser"):
            await self.browser.close()
            await self.playwright.stop()

    async def _set_content(self, expire_times: int) -> None:
        """Form báo 'code has expired' `expire_times` lần đầu, sau đó chấp nhận."""
        await self.page.set_content(
            OTP_FIELD
            + '<button type="submit" onclick="onSubmit()">Continue</button>'
            + '<p id="alertBox" role="alert"></p>'
            + "<script>let submitCount=0;"
            + f"const expireTimes={expire_times};"
            + "function onSubmit(){submitCount++;"
            + "alertBox.textContent = submitCount <= expireTimes ? 'Code has expired' : '';}"
            + "</script>"
        )

    async def _submit(self) -> None:
        await _submit_otp(
            self.page,
            self.account,
            CancellationToken(),
            ResponseObserver(self.page),
            "http://localhost:1455/",
        )

    async def test_retries_once_then_succeeds(self) -> None:
        await self._set_content(expire_times=1)
        await self._submit()
        self.assertEqual(await self.page.evaluate("submitCount"), 2, "phải submit đúng 2 lần")

    async def test_second_expiry_stops_without_third_attempt(self) -> None:
        await self._set_content(expire_times=2)
        with self.assertRaises(FlowStopped) as raised:
            await self._submit()
        self.assertEqual(raised.exception.code, ResultCode.EXPIRED_OTP)
        self.assertEqual(await self.page.evaluate("submitCount"), 2, "không được submit lần thứ 3")

    async def test_no_retry_when_first_attempt_accepted(self) -> None:
        await self._set_content(expire_times=0)
        await self._submit()
        self.assertEqual(await self.page.evaluate("submitCount"), 1)


if __name__ == "__main__":
    unittest.main()
