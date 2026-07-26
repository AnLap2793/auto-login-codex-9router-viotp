"""Vòng đời tài khoản: Chrome luôn được đóng, nhiều tài khoản chạy song song, không lộ secret.

Dùng Playwright giả nên chạy nhanh và không mở Chrome thật.
"""

from __future__ import annotations

import asyncio
import importlib.util
import unittest
from unittest import mock

if importlib.util.find_spec("playwright"):
    from login_codex_9router.accounts import Account
    from login_codex_9router.auth.automation import ResultCode, run_account
    from login_codex_9router.cancellation import CancellationToken
    from login_codex_9router.integrations.oauth_callback import CallbackServer
    from login_codex_9router.runner import run_text

PASSWORD = "mat-khau-rat-bi-mat"
SECRET = "JBSWY3DPEHPK3PXP"


class FakeBrowser:
    def __init__(self, failure: BaseException) -> None:
        self.closed = False
        self._failure = failure

    async def new_context(self):
        raise self._failure

    async def close(self) -> None:
        self.closed = True


class FakePlaywright:
    def __init__(self, failure: BaseException) -> None:
        self.browser = FakeBrowser(failure)
        outer = self

        class Chromium:
            async def launch(self, **_kwargs):
                return outer.browser

        self.chromium = Chromium()


@unittest.skipUnless(importlib.util.find_spec("playwright"), "playwright chưa được cài")
class BrowserCleanupTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.account = Account(1, "user@example.com", PASSWORD, SECRET)

    async def _run(self, failure: BaseException) -> tuple[FakePlaywright, object]:
        playwright = FakePlaywright(failure)
        with CallbackServer(port=0) as callback_server:
            result = await run_account(
                playwright,
                self.account,
                "http://localhost:20127",
                callback_server,
                CancellationToken(),
            )
        return playwright, result

    async def test_browser_closed_when_flow_raises(self) -> None:
        playwright, result = await self._run(RuntimeError("hỏng giữa chừng"))
        self.assertTrue(playwright.browser.closed, "Chrome phải được đóng khi lỗi")
        self.assertEqual(result.code, ResultCode.FAILED)

    async def test_browser_closed_when_cancelled(self) -> None:
        playwright, result = await self._run(asyncio.CancelledError())
        self.assertTrue(playwright.browser.closed, "Chrome phải được đóng khi hủy")
        self.assertEqual(result.code, ResultCode.CANCELLED)

    async def test_browser_closed_when_timeout(self) -> None:
        playwright, result = await self._run(TimeoutError("quá hạn"))
        self.assertTrue(playwright.browser.closed, "Chrome phải được đóng khi timeout")
        self.assertEqual(result.code, ResultCode.FAILED)

    async def test_failure_detail_never_contains_secrets(self) -> None:
        _, result = await self._run(RuntimeError(f"{PASSWORD} {SECRET}"))
        self.assertNotIn(PASSWORD, result.detail)
        self.assertNotIn(SECRET, result.detail)


@unittest.skipUnless(importlib.util.find_spec("playwright"), "playwright chưa được cài")
class ConcurrentRunTests(unittest.IsolatedAsyncioTestCase):
    TEXT = (
        f"first@example.com|{PASSWORD}|{SECRET}\n"
        f"second@example.com|{PASSWORD}|{SECRET}\n"
        "dong-sai-dinh-dang\n"
        f"third@example.com|{PASSWORD}|{SECRET}\n"
    )

    async def test_mixed_outcomes_keep_line_numbers(self) -> None:
        from login_codex_9router.auth.automation import AccountResult

        codes = {1: ResultCode.SUCCESS, 2: ResultCode.INVALID_PASSWORD, 4: ResultCode.SUCCESS}

        async def fake_run_account(_playwright, account, *_args, **_kwargs):
            await asyncio.sleep(0.01)
            return AccountResult(account, codes[account.line_number])

        updates = []
        with mock.patch("login_codex_9router.auth.automation.run_account", fake_run_account):
            results = await run_text(
                self.TEXT, "http://localhost:20127", updates.append, callback_port=0
            )

        self.assertEqual([r.account.line_number for r in results], [1, 2, 4])
        self.assertEqual([r.code for r in results], [codes[1], codes[2], codes[4]])
        # Dòng 3 sai định dạng: báo lỗi riêng, không làm hỏng các dòng còn lại.
        failed_line_3 = [u for u in updates if u.line_number == 3 and u.status == "failed"]
        self.assertEqual(len(failed_line_3), 1)

    async def test_cancellation_marks_remaining_accounts(self) -> None:
        cancellation = CancellationToken()

        async def fake_run_account(_playwright, account, *_args, **_kwargs):
            cancellation.cancel()
            await asyncio.sleep(30)
            raise AssertionError("phải bị hủy trước khi tới đây")

        with mock.patch("login_codex_9router.auth.automation.run_account", fake_run_account):
            results = await asyncio.wait_for(
                run_text(
                    self.TEXT,
                    "http://localhost:20127",
                    cancellation=cancellation,
                    callback_port=0,
                ),
                timeout=30,
            )

        self.assertEqual(len(results), 3)
        self.assertTrue(all(r.code == ResultCode.CANCELLED for r in results))

    async def test_status_updates_never_leak_secrets(self) -> None:
        from login_codex_9router.auth.automation import AccountResult

        async def fake_run_account(_playwright, account, *_args, **_kwargs):
            return AccountResult(account, ResultCode.SUCCESS)

        updates = []
        with mock.patch("login_codex_9router.auth.automation.run_account", fake_run_account):
            await run_text(self.TEXT, "http://localhost:20127", updates.append)

        rendered = " ".join(f"{u.masked_email} {u.status} {u.detail}" for u in updates)
        self.assertNotIn(PASSWORD, rendered)
        self.assertNotIn(SECRET, rendered)
        self.assertNotIn("first@example.com", rendered, "email phải được che")
        self.assertIn("fi***", rendered)


if __name__ == "__main__":
    unittest.main()
