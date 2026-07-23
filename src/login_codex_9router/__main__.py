import argparse
import asyncio
import os
import sys
from pathlib import Path

from .auth.automation import ResultCode
from .runner import StatusUpdate, run_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Kết nối tài khoản Codex vào 9router")
    parser.add_argument("accounts_file", type=Path, help="file email|password|2fa_secret")
    parser.add_argument("--headless", action="store_true", help="chạy Chrome ẩn")
    return parser


def print_status(update: StatusUpdate) -> None:
    detail = f" - {update.detail}" if update.detail else ""
    print(f"Dòng {update.line_number} [{update.masked_email}]: {update.status}{detail}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = build_parser().parse_args()
    try:
        text = args.accounts_file.read_text(encoding="utf-8-sig")
        results = asyncio.run(
            run_text(
                text,
                os.environ.get("NINE_ROUTER_HOST", ""),
                print_status,
                dashboard_password=os.environ.get("NINE_ROUTER_PASSWORD"),
                headless=args.headless,
            )
        )
    except (OSError, ValueError) as error:
        print(f"Lỗi: {error}", file=sys.stderr)
        raise SystemExit(2) from error

    if any(result.code != ResultCode.SUCCESS for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
