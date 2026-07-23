import asyncio
import unittest

from login_codex_9router.cancellation import CancellationToken


class CancellationTokenTests(unittest.TestCase):
    def test_cancel_is_thread_safe_and_raises(self) -> None:
        token = CancellationToken()
        self.assertFalse(token.cancelled)
        token.cancel()
        self.assertTrue(token.cancelled)
        with self.assertRaises(asyncio.CancelledError):
            token.raise_if_cancelled()


if __name__ == "__main__":
    unittest.main()
