import unittest

from login_codex_9router.auth.errors import AuthErrorCode, classify_response, classify_text


class AuthErrorTests(unittest.TestCase):
    def test_classifies_visible_messages(self) -> None:
        cases = {
            "Incorrect password": AuthErrorCode.INVALID_PASSWORD,
            "Your account is locked": AuthErrorCode.ACCOUNT_LOCKED,
            "This account has been deactivated": AuthErrorCode.ACCOUNT_DISABLED,
            "Too many attempts. Try again later": AuthErrorCode.RATE_LIMITED,
            "Incorrect verification code": AuthErrorCode.INVALID_OTP,
            "Verification code expired": AuthErrorCode.EXPIRED_OTP,
            "Account not found": AuthErrorCode.INVALID_EMAIL,
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(classify_text(text), expected)

    def test_classifies_http_status_without_payload(self) -> None:
        self.assertEqual(classify_response(429).code, AuthErrorCode.RATE_LIMITED)
        self.assertEqual(classify_response(401).code, AuthErrorCode.LOGIN_REJECTED)
        self.assertEqual(classify_response(403).code, AuthErrorCode.LOGIN_REJECTED)
        self.assertIsNone(classify_response(500))

    def test_safe_code_can_refine_generic_status(self) -> None:
        signal = classify_response(401, ("invalid_password",))
        self.assertEqual(signal.code, AuthErrorCode.INVALID_PASSWORD)
        self.assertEqual(signal.status, 401)


if __name__ == "__main__":
    unittest.main()
