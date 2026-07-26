"""Smoke test cho cửa sổ chính: dựng được widget và các command đã gắn đúng.

Không chạy mainloop nên không hiện cửa sổ và không bật hộp thoại cảnh báo.
"""

import tkinter as tk
import unittest
from unittest import mock


def _tk_available() -> bool:
    try:
        root = tk.Tk()
    except Exception:
        return False
    root.destroy()
    return True


@unittest.skipUnless(_tk_available(), "Tkinter không khả dụng")
class GuiSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        from login_codex_9router.gui import Application

        self.root = tk.Tk()
        self.root.withdraw()
        self.app = Application(self.root)

    def tearDown(self) -> None:
        self.root.destroy()

    def test_builds_every_widget(self) -> None:
        for name in (
            "host",
            "dashboard_password",
            "browser_mode",
            "accounts",
            "account_count",
            "choose_button",
            "clear_button",
            "viotp_summary",
            "viotp_button",
            "start_button",
            "stop_button",
            "summary",
            "stats_label",
            "results",
        ):
            self.assertTrue(hasattr(self.app, name), f"thiếu widget {name}")

    def test_buttons_have_commands(self) -> None:
        for button in (
            self.app.viotp_button,
            self.app.choose_button,
            self.app.clear_button,
            self.app.start_button,
            self.app.stop_button,
        ):
            self.assertTrue(str(button.cget("command")), "nút chưa gắn command")

    def test_account_count_updates_from_text(self) -> None:
        self.app.accounts.insert("1.0", "a@example.com|pw|JBSWY3DPEHPK3PXP\nkhong-hop-le\n")
        self.app._update_account_count()
        text = self.app.account_count.cget("text")
        self.assertIn("1 tài khoản", text)
        self.assertIn("1 dòng lỗi", text)

    def test_stop_button_enabled_only_while_running(self) -> None:
        self.app._set_running(True)
        self.assertEqual(str(self.app.stop_button.cget("state")), "normal")
        self.assertEqual(str(self.app.start_button.cget("state")), "disabled")
        self.app._set_running(False)
        self.assertEqual(str(self.app.stop_button.cget("state")), "disabled")
        self.assertEqual(str(self.app.start_button.cget("state")), "normal")

    def test_completion_summary_reports_counts_not_just_done(self) -> None:
        self.app.statuses = {1: "success", 2: "success", 3: "invalid_password", 4: "cancelled"}
        text = self.app._completion_text()
        self.assertIn("thành công 2/4", text)
        self.assertIn("thất bại 1", text)
        self.assertIn("đã dừng 1", text)

    def test_completion_summary_without_accounts(self) -> None:
        self.app.statuses = {}
        self.assertEqual(self.app._completion_text(), "Không có tài khoản nào để chạy")

    def test_completion_summary_hides_zero_counts(self) -> None:
        self.app.statuses = {1: "success", 2: "success"}
        text = self.app._completion_text()
        self.assertIn("thành công 2/2", text)
        self.assertNotIn("thất bại", text)
        self.assertNotIn("đã dừng", text)

    def test_closing_while_running_cancels_and_waits(self) -> None:
        from login_codex_9router.cancellation import CancellationToken

        worker = mock.Mock()
        worker.is_alive.return_value = True
        self.app.worker = worker
        self.app.cancellation = CancellationToken()

        with (
            mock.patch("login_codex_9router.gui.messagebox.askokcancel", return_value=True),
            mock.patch.object(self.app, "_persist_app_config"),
        ):
            self.app._on_close()

        self.assertTrue(self.app.closing)
        self.assertTrue(self.app.cancellation.cancelled)
        self.assertTrue(self.root.winfo_exists(), "không được destroy khi worker còn chạy")

    def test_closing_while_running_can_be_declined(self) -> None:
        worker = mock.Mock()
        worker.is_alive.return_value = True
        self.app.worker = worker

        with (
            mock.patch("login_codex_9router.gui.messagebox.askokcancel", return_value=False),
            mock.patch.object(self.app, "_persist_app_config") as persist,
        ):
            self.app._on_close()

        self.assertFalse(self.app.closing)
        persist.assert_not_called()

    def test_viotp_overlay_adds_and_removes_backdrop(self) -> None:
        self.assertIsNone(self.app.viotp_backdrop)
        self.app._open_viotp()
        backdrop = self.app.viotp_backdrop
        self.assertIsNotNone(backdrop)
        self.assertTrue(backdrop.winfo_exists())
        self.assertTrue(backdrop.winfo_ismapped() or backdrop.place_info())

        self.app.viotp_dialog.close()
        self.assertIsNone(self.app.viotp_backdrop)
        self.assertIsNone(self.app.viotp_dialog)
        self.assertFalse(backdrop.winfo_exists(), "backdrop phải bị hủy khi đóng modal")

    def test_reopening_viotp_overlay_does_not_stack_backdrops(self) -> None:
        self.app._open_viotp()
        first = self.app.viotp_backdrop
        self.app._open_viotp()
        self.assertIs(self.app.viotp_backdrop, first, "không được tạo backdrop thứ hai")
        self.app.viotp_dialog.close()

    def _seed_waiting_account(self, line: int = 1, status: str = "waiting_manual"):
        from login_codex_9router.cancellation import CancellationToken

        token = CancellationToken()
        self.app._set_running(True)
        self.app.results.insert("", "end", iid=str(line), values=(line, "us***@e.com", status, ""))
        self.app.statuses[line] = status
        self.app.account_tokens[line] = token
        self.app.results.selection_set(str(line))
        return token

    def test_skip_button_enabled_only_for_active_account(self) -> None:
        self._seed_waiting_account()
        self.app._refresh_skip_button()
        self.assertEqual(str(self.app.skip_button.cget("state")), "normal")

        self.app.statuses[1] = "success"
        self.app._refresh_skip_button()
        self.assertEqual(
            str(self.app.skip_button.cget("state")), "disabled", "tài khoản đã xong thì bỏ qua vô nghĩa"
        )

    def test_skip_button_cancels_only_that_account(self) -> None:
        first = self._seed_waiting_account(line=1)
        second = self._seed_waiting_account(line=2)
        self.app.results.selection_set("1")

        self.app._refresh_skip_button()
        self.app._skip_selected()

        self.assertTrue(first.cancelled)
        self.assertFalse(second.cancelled, "không được đụng tới tài khoản khác")

    def test_skip_button_disabled_when_not_running(self) -> None:
        self._seed_waiting_account()
        self.app._set_running(False)
        self.assertEqual(str(self.app.skip_button.cget("state")), "disabled")

    def test_stats_show_waiting_count(self) -> None:
        self.app.statuses = {1: "waiting_manual", 2: "running", 3: "success"}
        self.assertIn("Chờ xác minh 1", self.app._stats_text())
        self.app.statuses = {1: "running", 2: "success"}
        self.assertNotIn("Chờ xác minh", self.app._stats_text())

    def test_worker_stopped_always_unlocks_ui(self) -> None:
        """Worker chết vì BaseException thì không có sự kiện done/error. Nếu chỉ mở khóa
        ở hai nhánh đó, toàn bộ giao diện kẹt disabled và chỉ khởi động lại app mới thoát."""
        self.app._set_running(True)
        self.app.events.put(("worker_stopped", ""))
        self.app._drain_events()
        self.assertFalse(self.app.running)
        self.assertEqual(str(self.app.start_button.cget("state")), "normal")
        self.assertEqual(str(self.app.host.cget("state")), "normal")

    def test_orphaned_backdrop_is_cleared_on_reopen(self) -> None:
        """Overlay chết mà không gọi on_close sẽ để lại backdrop phủ kín cửa sổ, nuốt mọi
        thao tác chuột. Lần mở sau phải dọn nó thay vì chồng thêm lớp mới."""
        self.app._open_viotp()
        orphan = self.app.viotp_backdrop
        self.app.viotp_dialog.destroy()  # huỷ thẳng, không qua close() nên on_close không chạy
        self.app.viotp_dialog = None

        self.app._open_viotp()
        self.assertFalse(orphan.winfo_exists(), "backdrop mồ côi phải bị dọn")
        self.assertIsNot(self.app.viotp_backdrop, orphan)
        self.app.viotp_dialog.close()
        self.assertIsNone(self.app.viotp_backdrop)

    def test_backdrop_removed_when_overlay_construction_fails(self) -> None:
        with mock.patch(
            "login_codex_9router.gui.ViotpConfigOverlay", side_effect=RuntimeError("hỏng")
        ):
            with self.assertRaises(RuntimeError):
                self.app._open_viotp()
        self.assertIsNone(self.app.viotp_backdrop, "không được để backdrop treo lại")

    def test_force_close_only_when_worker_still_alive(self) -> None:
        # _force_close gọi os._exit nên chỉ kiểm tra nhánh thoát sớm, không kích hoạt nhánh kill.
        self.app.closing = False
        self.app.worker = None
        with mock.patch("login_codex_9router.gui.os._exit") as force_exit:
            self.app._force_close()
        force_exit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
