import unittest

from login_codex_9router.accounts import parse_accounts


class ParseAccountsTests(unittest.TestCase):
    def test_parses_valid_lines_and_reports_invalid_lines(self) -> None:
        accounts, errors = parse_accounts(
            "\nuser@example.com|password|SECRET\ninvalid\nother@example.com||SECRET\n"
        )

        self.assertEqual([account.line_number for account in accounts], [2])
        self.assertEqual(accounts[0].email, "user@example.com")
        self.assertEqual([error.line_number for error in errors], [3, 4])

    def test_masked_email_does_not_expose_local_part(self) -> None:
        accounts, _ = parse_accounts("sensitive@example.com|password|SECRET")

        self.assertEqual(accounts[0].masked_email, "se*******@example.com")


if __name__ == "__main__":
    unittest.main()
