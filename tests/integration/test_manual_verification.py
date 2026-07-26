"""Chờ người dùng tự xử lý CAPTCHA / xác minh điện thoại trong cửa sổ Chrome.

Ứng dụng không tự điền gì ở các bước này — chỉ giữ cửa sổ mở, theo dõi xem bước chặn
đã qua chưa, rồi chạy tiếp.
"""

from __future__ import annotations

import asyncio
import importlib.util
import unittest

if importlib.util.find_spec("playwright"):
    from playwright.async_api import async_playwright

    from login_codex_9router.accounts import Account
    from login_codex_9router.auth.openai_login import _wait_for_manual_resolution, complete_openai_login
    from login_codex_9router.auth.results import WAITING_MANUAL_STATUS, FlowStopped, ResultCode
    from login_codex_9router.cancellation import CancellationToken

PHONE_PAGE = '<label>Phone number<input type="tel"></label><div id="root"></div>'
CALLBACK_PREFIX = "http://localhost:1455/"


@unittest.skipUnless(importlib.util.find_spec("playwright"), "playwright chưa được cài")
class ManualVerificationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.playwright = await async_playwright().start()
        try:
            self.browser = await self.playwright.chromium.launch(channel="chrome", headless=True)
        except Exception as error:
            await self.playwright.stop()
            self.skipTest(f"Chrome không khả dụng: {type(error).__name__}")
        self.page = await self.browser.new_page()
        self.account = Account(1, "user@example.com", "pw", "JBSWY3DPEHPK3PXP")
        self.progress: list[tuple[str, str]] = []

    async def asyncTearDown(self) -> None:
        if hasattr(self, "browser"):
            await self.browser.close()
            await self.playwright.stop()

    def _record(self, status: str, detail: str) -> None:
        self.progress.append((status, detail))

    async def _wait(self, timeout: float, token: CancellationToken | None = None) -> bool:
        return await _wait_for_manual_resolution(
            self.page,
            "phone",
            token or CancellationToken(),
            timeout,
            CALLBACK_PREFIX,
            self._record,
        )

    async def test_resolves_when_user_clears_the_blocker(self) -> None:
        await self.page.set_content(
            PHONE_PAGE
            + "<script>setTimeout(() => document.querySelector('input[type=tel]')"
            + ".closest('label').remove(), 1200)</script>"
        )
        self.assertTrue(await self._wait(timeout=20))

    async def test_reports_waiting_status_with_minutes(self) -> None:
        await self.page.set_content(PHONE_PAGE)
        await self._wait(timeout=2)
        self.assertEqual(self.progress[0][0], WAITING_MANUAL_STATUS)
        self.assertIn("xác minh số điện thoại", self.progress[0][1])
        self.assertIn("phút", self.progress[0][1])

    async def test_gives_up_after_timeout(self) -> None:
        await self.page.set_content(PHONE_PAGE)
        self.assertFalse(await self._wait(timeout=2))

    async def test_skip_button_cancels_the_wait(self) -> None:
        await self.page.set_content(PHONE_PAGE)
        token = CancellationToken()
        waiter = asyncio.create_task(self._wait(timeout=60, token=token))
        await asyncio.sleep(0.4)
        token.cancel()  # nút "Bỏ qua tài khoản đang chọn"
        with self.assertRaises(asyncio.CancelledError):
            await waiter

    async def test_parent_stop_also_cancels_the_wait(self) -> None:
        await self.page.set_content(PHONE_PAGE)
        parent = CancellationToken()
        waiter = asyncio.create_task(self._wait(timeout=60, token=parent.child()))
        await asyncio.sleep(0.4)
        parent.cancel()  # nút Dừng
        with self.assertRaises(asyncio.CancelledError):
            await waiter


@unittest.skipUnless(importlib.util.find_spec("playwright"), "playwright chưa được cài")
class BlockerPolicyTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_stops_immediately_when_waiting_disabled(self) -> None:
        """Chế độ chạy ẩn: không có cửa sổ để thao tác nên giữ nguyên hành vi dừng ngay."""
        await self.page.set_content(PHONE_PAGE)
        with self.assertRaises(FlowStopped) as raised:
            await complete_openai_login(self.page, self.account, CancellationToken(), manual_timeout=0)
        self.assertEqual(raised.exception.code, ResultCode.PHONE_VERIFICATION_REQUIRED)
        self.assertIn("cần xác minh số điện thoại thủ công", str(raised.exception))

    async def test_reports_timeout_reason_when_user_does_not_act(self) -> None:
        await self.page.set_content(PHONE_PAGE)
        with self.assertRaises(FlowStopped) as raised:
            await complete_openai_login(self.page, self.account, CancellationToken(), manual_timeout=2)
        self.assertEqual(raised.exception.code, ResultCode.PHONE_VERIFICATION_REQUIRED)
        self.assertIn("hết thời gian chờ", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
