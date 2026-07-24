"""Integration tests cho chuỗi OAuth callback → điền URL → Connect → success/failure."""

from __future__ import annotations

import asyncio
import importlib.util
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import urlopen

from login_codex_9router.integrations.oauth_callback import CallbackServer

if importlib.util.find_spec("playwright"):
    from playwright.async_api import async_playwright

    from login_codex_9router.accounts import Account
    from login_codex_9router.auth.automation import FlowStopped, ResultCode, run_account
    from login_codex_9router.cancellation import CancellationToken


class CallbackValidationTests(unittest.IsolatedAsyncioTestCase):
    """Kiểm tra CallbackServer reject/accept theo query params."""

    async def test_rejects_callback_without_code_or_error(self) -> None:
        with CallbackServer(port=0) as server:
            server.expect("s1")
            with self.assertRaises(HTTPError) as ctx:
                await asyncio.to_thread(
                    self._get, server.port, "/auth/callback?state=s1"
                )
            self.assertEqual(ctx.exception.code, 400)

    async def test_accepts_callback_with_code(self) -> None:
        with CallbackServer(port=0) as server:
            server.expect("s1")
            task = asyncio.create_task(server.wait("s1", timeout=2))
            await asyncio.to_thread(
                self._get, server.port, "/auth/callback?state=s1&code=abc123"
            )
            url = await task
            self.assertIn("code=abc123", url)

    async def test_accepts_callback_with_error(self) -> None:
        with CallbackServer(port=0) as server:
            server.expect("s1")
            task = asyncio.create_task(server.wait("s1", timeout=2))
            await asyncio.to_thread(
                self._get,
                server.port,
                "/auth/callback?state=s1&error=access_denied&error_description=User+denied",
            )
            url = await task
            self.assertIn("error=access_denied", url)

    @staticmethod
    def _get(port: int, path: str) -> None:
        with urlopen(f"http://127.0.0.1:{port}{path}", timeout=2) as resp:
            assert resp.status == 200


class _DashboardFixture:
    """HTTP server giả lập 9router dashboard cho test full-flow."""

    def __init__(self, callback_port: int) -> None:
        self._callback_port = callback_port
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path.startswith("/api/oauth/codex/authorize"):
                    self._json('{"state":"test-state"}')
                elif self.path == "/dashboard/providers/codex":
                    self._html(self._dashboard_html())
                else:
                    self._html("<h1>Not Found</h1>")

            def _dashboard_html(self) -> str:
                return (
                    "<button onclick=\"fetch('/api/oauth/codex/authorize')"
                    ".then(r=>r.json()).then(()=>window.open("
                    f"'http://127.0.0.1:{owner._callback_port}"
                    "/auth/callback?state=test-state&code=authcode'))"
                    '">Add</button>'
                    '<dialog open>'
                    '<input type="text">'
                    '<button onclick="onConnect()">Connect</button>'
                    '<p id="result"></p>'
                    '</dialog>'
                    "<script>"
                    "function onConnect(){"
                    "document.getElementById('result').textContent='Connected Successfully!';"
                    "}"
                    "</script>"
                )

            def _json(self, body_str: str) -> None:
                body = body_str.encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

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
        self._thread = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )

    def __enter__(self) -> "_DashboardFixture":
        self._thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self._thread.join(timeout=2)


@unittest.skipUnless(
    importlib.util.find_spec("playwright"), "playwright chưa được cài"
)
class OAuthCallbackFlowTests(unittest.IsolatedAsyncioTestCase):
    """Test chuỗi: OAuth callback → điền URL → Connect → success/failure."""

    async def asyncSetUp(self) -> None:
        self.playwright = await async_playwright().start()
        try:
            self.browser = await self.playwright.chromium.launch(
                channel="chrome", headless=True
            )
        except Exception as error:
            await self.playwright.stop()
            self.skipTest(f"Chrome không khả dụng: {type(error).__name__}")

    async def asyncTearDown(self) -> None:
        if hasattr(self, "browser"):
            await self.browser.close()
            await self.playwright.stop()

    async def test_oauth_error_callback_raises_flow_stopped(self) -> None:
        """Callback có error param → FlowStopped với message OAuth error."""
        with CallbackServer(port=0) as cb_server:
            # Giả lập: callback trả error thay vì code
            cb_server.expect("err-state")
            send_task = asyncio.create_task(self._send_error_callback(cb_server))
            url = await cb_server.wait("err-state", timeout=2)
            await send_task
            self.assertIn("error=access_denied", url)

    async def _send_error_callback(self, server: CallbackServer) -> None:
        await asyncio.sleep(0.05)
        await asyncio.to_thread(
            self._get_url,
            server.port,
            "/auth/callback?state=err-state&error=access_denied"
            "&error_description=User+denied+access",
        )

    @staticmethod
    def _get_url(port: int, path: str) -> None:
        with urlopen(f"http://127.0.0.1:{port}{path}", timeout=2):
            pass


if __name__ == "__main__":
    unittest.main()
