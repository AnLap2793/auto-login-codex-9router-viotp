import unittest

from login_codex_9router.config import normalize_host


class NormalizeHostTests(unittest.TestCase):
    def test_normalizes_host_and_removes_path(self) -> None:
        self.assertEqual(normalize_host("http://localhost:20127/path"), "http://localhost:20127")

    def test_rejects_unsupported_or_incomplete_url(self) -> None:
        for value in (
            "localhost:20127",
            "file:///tmp/app",
            "",
            "http://example.com:bad",
            "http://example.com:99999",
            "http://user:password@example.com",
            "http://example.com\\attacker.test",
            "http://example .com",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_host(value)


if __name__ == "__main__":
    unittest.main()
