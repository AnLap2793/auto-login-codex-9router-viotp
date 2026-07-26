import argparse
import asyncio
import os
import signal
import sys
from pathlib import Path

from .accounts import parse_accounts
from .auth.automation import ResultCode
from .auth.results import MANUAL_VERIFICATION_TIMEOUT
from .cancellation import CancellationToken
from .runner import CallbackPortBusyError, StatusUpdate, run_text

EXIT_OK = 0
EXIT_INCOMPLETE = 1
EXIT_BAD_INPUT = 2
EXIT_INTERRUPTED = 130


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Kết nối tài khoản Codex vào 9router")
    parser.add_argument("accounts_file", type=Path, help="file email|password|2fa_secret")
    parser.add_argument("--headless", action="store_true", help="chạy Chrome ẩn")
    parser.add_argument(
        "--manual-timeout",
        type=float,
        default=None,
        metavar="GIAY",
        help=(
            "số giây chờ bạn tự xử lý CAPTCHA hoặc xác minh điện thoại trong cửa sổ Chrome "
            f"(mặc định {MANUAL_VERIFICATION_TIMEOUT:.0f}; 0 = dừng ngay; luôn 0 khi --headless)"
        ),
    )
    return parser


def print_status(update: StatusUpdate) -> None:
    detail = f" - {update.detail}" if update.detail else ""
    print(f"Dòng {update.line_number} [{update.masked_email}]: {update.status}{detail}")


def _install_interrupt_handler(cancellation: CancellationToken) -> None:
    """Ctrl+C lần đầu chỉ bật cờ hủy để `run_text` kịp đóng Chrome, thay vì ném ngay
    KeyboardInterrupt làm hỏng bước dọn dẹp. Lần thứ hai thoát ngay, phòng khi
    Chrome không phản hồi và bước dọn dẹp treo vô hạn."""

    def _on_interrupt(_signum: int, _frame: object) -> None:
        if cancellation.cancelled:
            print("Thoát ngay theo yêu cầu; Chrome có thể còn sót lại.", file=sys.stderr)
            sys.stderr.flush()
            os._exit(EXIT_INTERRUPTED)
        print("Đang dừng và dọn Chrome… (Ctrl+C lần nữa để thoát ngay)", file=sys.stderr)
        cancellation.cancel()

    try:
        signal.signal(signal.SIGINT, _on_interrupt)
    except ValueError:
        # Không phải main thread: giữ nguyên handler mặc định.
        pass


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = build_parser().parse_args()

    try:
        text = args.accounts_file.read_text(encoding="utf-8-sig")
    except OSError as error:
        print(f"Lỗi: {error}", file=sys.stderr)
        raise SystemExit(EXIT_BAD_INPUT) from error

    # Không in lỗi dòng ở đây khi vẫn còn tài khoản hợp lệ: `run_text` sẽ báo từng dòng
    # qua `print_status`, in thêm ở đây sẽ thành báo hai lần trên hai luồng khác nhau.
    accounts, parse_errors = parse_accounts(text)
    if not accounts:
        for parse_error in parse_errors:
            print(f"Dòng {parse_error.line_number}: {parse_error.message}", file=sys.stderr)
        print("Lỗi: không có tài khoản hợp lệ nào trong file.", file=sys.stderr)
        raise SystemExit(EXIT_BAD_INPUT)

    cancellation = CancellationToken()
    _install_interrupt_handler(cancellation)
    try:
        results = asyncio.run(
            run_text(
                text,
                os.environ.get("NINE_ROUTER_HOST", ""),
                print_status,
                cancellation,
                os.environ.get("NINE_ROUTER_PASSWORD"),
                args.headless,
                manual_timeout=args.manual_timeout,
            )
        )
    except ValueError as error:
        print(f"Lỗi: {error}", file=sys.stderr)
        raise SystemExit(EXIT_BAD_INPUT) from error
    except (KeyboardInterrupt, asyncio.CancelledError):
        raise SystemExit(EXIT_INTERRUPTED) from None
    except CallbackPortBusyError as error:
        # Chưa tài khoản nào chạy, nên xếp cùng nhóm "không chạy được gì".
        print(f"Lỗi: {error}", file=sys.stderr)
        raise SystemExit(EXIT_BAD_INPUT) from error

    if cancellation.cancelled:
        raise SystemExit(EXIT_INTERRUPTED)
    if parse_errors or any(result.code != ResultCode.SUCCESS for result in results):
        raise SystemExit(EXIT_INCOMPLETE)


if __name__ == "__main__":
    main()
