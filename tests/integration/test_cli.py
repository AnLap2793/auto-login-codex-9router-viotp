"""Subprocess test cho CLI: exit code, encoding và thông báo lỗi.

Chỉ dùng các trường hợp thoát trước khi khởi chạy Chrome nên chạy nhanh và không cần
9router thật. Trường hợp exit code 1 do account thất bại cần Chrome, thuộc E2E.
"""

import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

EXIT_INCOMPLETE = 1
EXIT_BAD_INPUT = 2


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def _write(self, content: str, encoding: str = "utf-8") -> Path:
        path = Path(self.directory.name) / "accounts.txt"
        path.write_text(content, encoding=encoding)
        return path

    def _run(self, path: Path, host: str | None = None) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment["PYTHONIOENCODING"] = "utf-8"
        if host is None:
            environment.pop("NINE_ROUTER_HOST", None)
        else:
            environment["NINE_ROUTER_HOST"] = host
        return subprocess.run(
            [sys.executable, "-m", "login_codex_9router", str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
            timeout=120,
        )

    def test_missing_file_exits_bad_input(self) -> None:
        result = self._run(Path(self.directory.name) / "khong-ton-tai.txt")
        self.assertEqual(result.returncode, EXIT_BAD_INPUT)
        self.assertIn("Lỗi:", result.stderr)

    def test_empty_file_exits_bad_input(self) -> None:
        result = self._run(self._write("\n   \n\n"))
        self.assertEqual(result.returncode, EXIT_BAD_INPUT)
        self.assertIn("không có tài khoản hợp lệ", result.stderr)

    def test_all_lines_invalid_exits_bad_input(self) -> None:
        result = self._run(self._write("thieu-truong\nkhong-co-a-cong|pw|secret\n"))
        self.assertEqual(result.returncode, EXIT_BAD_INPUT)
        self.assertIn("Dòng 1", result.stderr)
        self.assertIn("Dòng 2", result.stderr)

    def test_reports_each_invalid_line_number(self) -> None:
        result = self._run(self._write("\nthieu-truong\n\nvan-thieu\n"))
        self.assertIn("Dòng 2", result.stderr)
        self.assertIn("Dòng 4", result.stderr)

    def test_invalid_host_exits_bad_input(self) -> None:
        result = self._run(self._write("user@example.com|pw|JBSWY3DPEHPK3PXP\n"), host="khong-phai-url")
        self.assertEqual(result.returncode, EXIT_BAD_INPUT)
        self.assertIn("HOST", result.stderr)

    def test_missing_host_env_exits_bad_input(self) -> None:
        result = self._run(self._write("user@example.com|pw|JBSWY3DPEHPK3PXP\n"))
        self.assertEqual(result.returncode, EXIT_BAD_INPUT)
        self.assertIn("HOST", result.stderr)

    def test_reads_file_with_utf8_bom(self) -> None:
        path = self._write("user@example.com|pw|JBSWY3DPEHPK3PXP\n", encoding="utf-8-sig")
        result = self._run(path, host="khong-phai-url")
        # BOM phải được bỏ qua: dòng 1 hợp lệ nên lỗi duy nhất là HOST, không phải định dạng.
        self.assertNotIn("định dạng", result.stderr)
        self.assertIn("HOST", result.stderr)

    def test_busy_callback_port_exits_bad_input_without_duplicate_line_errors(self) -> None:
        """Cổng 1455 bận: chưa tài khoản nào chạy nên phải là exit 2, không phải 1.
        Đồng thời kiểm tra lỗi dòng không bị in sẵn ra stderr khi vẫn còn account hợp lệ —
        `run_text` mới là nơi báo, in ở cả hai chỗ sẽ thành báo trùng trên hai luồng."""
        squatter = socket.socket()
        squatter.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            squatter.bind(("127.0.0.1", 1455))
            squatter.listen(1)
        except OSError:
            squatter.close()
            self.skipTest("cổng 1455 đang bị tiến trình khác giữ độc quyền")

        try:
            result = self._run(
                self._write(f"user@example.com|pw|JBSWY3DPEHPK3PXP\ndong-sai\n"),
                host="http://localhost:20127",
            )
        finally:
            squatter.close()

        self.assertEqual(result.returncode, EXIT_BAD_INPUT)
        self.assertIn("1455", result.stderr)
        self.assertNotIn("Dòng 2:", result.stderr)

    def test_never_prints_password_or_secret(self) -> None:
        result = self._run(
            self._write("user@example.com|sieu-mat-khau|JBSWY3DPEHPK3PXP\n"), host="khong-phai-url"
        )
        combined = result.stdout + result.stderr
        self.assertNotIn("sieu-mat-khau", combined)
        self.assertNotIn("JBSWY3DPEHPK3PXP", combined)


if __name__ == "__main__":
    unittest.main()
