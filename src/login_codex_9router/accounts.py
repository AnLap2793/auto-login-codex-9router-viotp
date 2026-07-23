from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Account:
    line_number: int
    email: str
    password: str
    two_factor_secret: str

    @property
    def masked_email(self) -> str:
        local, separator, domain = self.email.partition("@")
        if not separator:
            return "***"
        visible = local[:2]
        return f"{visible}{'*' * max(3, len(local) - len(visible))}@{domain}"


@dataclass(frozen=True, slots=True)
class ParseError:
    line_number: int
    message: str


def parse_accounts(text: str) -> tuple[list[Account], list[ParseError]]:
    accounts: list[Account] = []
    errors: list[ParseError] = []

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        parts = [part.strip() for part in line.split("|")]
        if len(parts) != 3 or not all(parts):
            errors.append(ParseError(line_number, "định dạng phải là email|password|2fa_secret"))
            continue

        email, password, secret = parts
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            errors.append(ParseError(line_number, "email không hợp lệ"))
            continue

        accounts.append(Account(line_number, email, password, secret))

    return accounts, errors


def load_accounts(path: Path) -> tuple[list[Account], list[ParseError]]:
    return parse_accounts(path.read_text(encoding="utf-8-sig"))
