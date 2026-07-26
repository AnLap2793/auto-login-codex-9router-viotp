"""Chạy toàn bộ test và chặn build khi test browser bị bỏ qua âm thầm.

Phân biệt hai loại skip:

- Skip hợp lệ: E2E cần biến môi trường và tài khoản thật, mặc định không chạy.
- Skip nguy hiểm: thiếu Chrome / Playwright / Tkinter. Build vẫn "xanh" nhưng thực chất
  chưa kiểm tra gì về browser hay GUI — đóng gói EXE lúc này là đóng gói mù.

Đặt `ALLOW_SKIPPED_BROWSER_TESTS=1` để hạ xuống mức cảnh báo.
"""

import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Allow-list, không phải deny-list: chỉ những lý do skip dưới đây là cố ý. Mọi skip khác
# đều bị coi là môi trường thiếu thứ gì đó và chặn build. Deny-list sẽ bỏ lọt các skip mới
# thêm về sau — ví dụ "cổng 1455 đã bị tiến trình khác chiếm" hay "Windows DPAPI required".
ALLOWED_SKIP_MARKERS = ("thiếu E2E environment variables",)


def main() -> int:
    tests = unittest.defaultTestLoader.discover(start_dir=str(PROJECT_ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(tests)

    if not result.wasSuccessful():
        return 1

    blocked = [
        (test, reason)
        for test, reason in result.skipped
        if not any(marker in reason for marker in ALLOWED_SKIP_MARKERS)
    ]
    if not blocked:
        return 0

    print("\n" + "=" * 70, file=sys.stderr)
    print(f"CANH BAO: {len(blocked)} test bi bo qua ngoai y muon:", file=sys.stderr)
    for test, reason in blocked:
        print(f"  - {test}: {reason}", file=sys.stderr)
    print("=" * 70, file=sys.stderr)

    if os.environ.get("ALLOW_SKIPPED_BROWSER_TESTS") == "1":
        print("ALLOW_SKIPPED_BROWSER_TESTS=1 -> van tiep tuc build.", file=sys.stderr)
        return 0

    print(
        "Khac phuc moi truong (Chrome, Playwright, Tkinter, cong 1455) roi chay lai, hoac dat "
        "ALLOW_SKIPPED_BROWSER_TESTS=1 neu chap nhan build ma chua kiem tra day du.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
