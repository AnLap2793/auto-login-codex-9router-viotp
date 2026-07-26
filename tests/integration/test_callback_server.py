import asyncio
import socket
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

from login_codex_9router.integrations.oauth_callback import CallbackServer


class CallbackServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_routes_concurrent_callbacks_by_state(self) -> None:
        with CallbackServer(port=0) as server:
            server.expect("state-a")
            server.expect("state-b")
            first = asyncio.create_task(server.wait("state-a", timeout=2))
            second = asyncio.create_task(server.wait("state-b", timeout=2))

            await asyncio.gather(
                asyncio.to_thread(self._send, server.port, "state-b", "code-b"),
                asyncio.to_thread(self._send, server.port, "state-a", "code-a"),
            )

            self.assertIn("code=code-a", await first)
            self.assertIn("code=code-b", await second)

    async def test_rejects_unexpected_state(self) -> None:
        with CallbackServer(port=0) as server:
            with self.assertRaises(HTTPError) as error:
                await asyncio.to_thread(self._send, server.port, "unexpected", "code")
            self.assertEqual(error.exception.code, 400)

    async def test_busy_callback_port_reports_actionable_error(self) -> None:
        from login_codex_9router.runner import run_text

        blocker = socket.socket()
        blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            blocker.bind(("127.0.0.1", 1455))
        except OSError:
            blocker.close()
            self.skipTest("cổng 1455 đã bị tiến trình khác chiếm")
        blocker.listen(1)
        try:
            with self.assertRaises(RuntimeError) as raised:
                await run_text(
                    "user@example.com|password|JBSWY3DPEHPK3PXP",
                    "http://localhost:20127",
                )
        finally:
            blocker.close()
        self.assertIn("1455", str(raised.exception))

    async def test_refuses_port_already_bound_without_listening(self) -> None:
        """Windows bật SO_REUSEADDR sẽ cho bind đè lên cổng đang dùng, và bên bind sau
        nhận kết nối — tức mã ủy quyền OAuth có thể rơi vào tiến trình khác. Bind độc quyền
        phải chặn kể cả khi socket kia mới bind mà chưa listen (probe không thấy được)."""
        from login_codex_9router.integrations.oauth_callback import PortBusyError

        squatter = socket.socket()
        squatter.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            squatter.bind(("127.0.0.1", 1455))
        except OSError:
            squatter.close()
            self.skipTest("cổng 1455 đang bị tiến trình khác giữ độc quyền")
        try:
            with self.assertRaises(PortBusyError):
                CallbackServer()
        finally:
            squatter.close()

    async def test_second_server_cannot_share_the_port(self) -> None:
        from login_codex_9router.integrations.oauth_callback import PortBusyError

        with CallbackServer() as first:
            self.assertEqual(first.port, 1455)
            with self.assertRaises(PortBusyError):
                CallbackServer()

    async def test_port_is_released_after_close(self) -> None:
        with CallbackServer() as first:
            self.assertEqual(first.port, 1455)
        with CallbackServer() as second:
            self.assertEqual(second.port, 1455, "cổng phải dùng lại được sau khi đóng")

    @staticmethod
    def _send(port: int, state: str, code: str) -> None:
        with urlopen(
            f"http://127.0.0.1:{port}/auth/callback?state={state}&code={code}", timeout=2
        ) as response:
            assert response.status == 200


if __name__ == "__main__":
    unittest.main()
