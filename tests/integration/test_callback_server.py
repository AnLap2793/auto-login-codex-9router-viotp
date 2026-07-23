import asyncio
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

    @staticmethod
    def _send(port: int, state: str, code: str) -> None:
        with urlopen(
            f"http://127.0.0.1:{port}/auth/callback?state={state}&code={code}", timeout=2
        ) as response:
            assert response.status == 200


if __name__ == "__main__":
    unittest.main()
