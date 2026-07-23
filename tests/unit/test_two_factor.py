import unittest

from login_codex_9router.auth.totp import TwoFactorError, generate_totp


class TwoFactorTests(unittest.TestCase):
    def test_matches_rfc_6238_sha1_vectors(self) -> None:
        secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
        vectors = {
            59: "94287082",
            1_111_111_109: "07081804",
            1_111_111_111: "14050471",
            1_234_567_890: "89005924",
            2_000_000_000: "69279037",
            20_000_000_000: "65353130",
        }
        for timestamp, expected in vectors.items():
            with self.subTest(timestamp=timestamp):
                self.assertEqual(generate_totp(secret, timestamp, digits=8), expected)

    def test_accepts_spaces_and_lowercase(self) -> None:
        self.assertEqual(
            generate_totp("gezd gnbv gy3t qojq gezd gnbv gy3t qojq", 59, digits=8),
            "94287082",
        )

    def test_rejects_invalid_secret(self) -> None:
        for secret in ("", "NOT!BASE32"):
            with self.subTest(secret=secret), self.assertRaises(TwoFactorError):
                generate_totp(secret, 59)


if __name__ == "__main__":
    unittest.main()
