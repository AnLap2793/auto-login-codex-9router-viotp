import asyncio
import importlib.util
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

if importlib.util.find_spec("playwright"):
    from playwright.async_api import async_playwright

    from login_codex_9router.auth.automation import _login_dashboard, _open_oauth
    from login_codex_9router.cancellation import CancellationToken


class FixtureServer:
    def __init__(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path == "/login":
                    self._html(
                        '<label>Password<input type="password" id="password"></label>'
                        '<button onclick="login()">Login</button>'
                        '<script>function login(){if(password.value===\'secret\') location=\'/dashboard\'; '
                        "else document.body.insertAdjacentHTML('beforeend','<p>Invalid password</p>')}</script>"
                    )
                elif self.path == "/dashboard":
                    self._html("<h1>Dashboard</h1>")
                elif self.path == "/oauth":
                    self._html("<h1>OAuth</h1>")
                elif self.path.startswith("/api/oauth/codex/authorize"):
                    body = b'{"state":"fixture-state"}'
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self._html(
                        "<button onclick=\"fetch('/api/oauth/codex/authorize')"
                        ".then(r=>r.json()).then(()=>window.open('/oauth'))\">Add</button>"
                    )

            def _html(self, text: str) -> None:
                body = text.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, _format: str, *args: object) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> "FixtureServer":
        self.thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


@unittest.skipUnless(importlib.util.find_spec("playwright"), "playwright chưa được cài")
class AutomationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.playwright = await async_playwright().start()
        try:
            self.browser = await self.playwright.chromium.launch(channel="chrome", headless=True)
        except Exception as error:
            await self.playwright.stop()
            self.skipTest(f"Chrome không khả dụng: {type(error).__name__}")

    async def asyncTearDown(self) -> None:
        if hasattr(self, "browser"):
            await self.browser.close()
            await self.playwright.stop()

    async def test_dashboard_password_login(self) -> None:
        with FixtureServer() as server:
            page = await self.browser.new_page()
            await page.goto(f"http://127.0.0.1:{server.port}/login")
            await _login_dashboard(page, "secret", CancellationToken())
            self.assertTrue(page.url.endswith("/dashboard"))

    async def test_catches_popup_opened_immediately_after_authorize(self) -> None:
        with FixtureServer() as server:
            context = await self.browser.new_context()
            page = await context.new_page()
            await page.goto(f"http://127.0.0.1:{server.port}/")
            popup, state = await _open_oauth(context, page)
            self.assertEqual(state, "fixture-state")
            self.assertTrue(popup.url.endswith("/oauth"))
            await context.close()

    async def test_run_account_passes_headless_to_chrome(self) -> None:
        from login_codex_9router.accounts import Account
        from login_codex_9router.auth.automation import ResultCode, run_account
        from login_codex_9router.integrations.oauth_callback import CallbackServer
        from login_codex_9router.cancellation import CancellationToken

        class Browser:
            async def new_context(self):
                raise RuntimeError("stop after launch")

            async def close(self):
                pass

        class Chromium:
            def __init__(self) -> None:
                self.kwargs = None

            async def launch(self, **kwargs):
                self.kwargs = kwargs
                return Browser()

        class Playwright:
            def __init__(self) -> None:
                self.chromium = Chromium()

        playwright = Playwright()
        account = Account(1, "user@example.com", "password", "JBSWY3DPEHPK3PXP")
        with CallbackServer(port=0) as callback_server:
            result = await run_account(
                playwright,
                account,
                "http://localhost:20127",
                callback_server,
                CancellationToken(),
                headless=True,
            )
        self.assertEqual(playwright.chromium.kwargs, {"channel": "chrome", "headless": True})
        self.assertEqual(result.code, ResultCode.FAILED)


if __name__ == "__main__":
    unittest.main()
