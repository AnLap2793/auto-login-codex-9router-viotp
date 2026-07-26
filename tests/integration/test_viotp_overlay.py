"""Test modal VIOTP: lưu, hủy, Escape, grab và xử lý response đến muộn.

Không gọi mạng thật — chỉ nạp sự kiện vào hàng đợi của overlay như thread kiểm tra token
vẫn làm, rồi kiểm tra chuyển trạng thái.
"""

import tkinter as tk
import unittest


def _tk_available() -> bool:
    try:
        root = tk.Tk()
    except Exception:
        return False
    root.destroy()
    return True


@unittest.skipUnless(_tk_available(), "Tkinter không khả dụng")
class ViotpOverlayTests(unittest.TestCase):
    def setUp(self) -> None:
        from login_codex_9router.theme import configure_style

        self.root = tk.Tk()
        self.root.withdraw()
        configure_style()
        self.saved: list = []
        self.closed = 0

    def tearDown(self) -> None:
        self.root.destroy()

    def _overlay(self, current=None):
        from login_codex_9router.viotp_dialog import ViotpConfigOverlay

        def on_close() -> None:
            self.closed += 1

        return ViotpConfigOverlay(self.root, current, self.saved.append, on_close)

    def test_escape_closes_and_releases_grab(self) -> None:
        overlay = self._overlay()
        self.assertEqual(self.root.grab_current(), overlay)
        overlay._escape()
        self.assertFalse(overlay.winfo_exists())
        self.assertEqual(self.closed, 1)
        self.assertIsNone(self.root.grab_current())

    def test_close_button_reports_close_once(self) -> None:
        overlay = self._overlay()
        overlay.close()
        overlay.close()
        self.assertEqual(self.closed, 1, "close lần hai không được gọi lại on_close")

    def test_save_disabled_until_token_verified(self) -> None:
        overlay = self._overlay()
        overlay.token.insert(0, "token-chua-kiem-tra")
        overlay._token_changed()
        self.assertEqual(str(overlay.save_button.cget("state")), "disabled")
        overlay._save()
        self.assertEqual(self.saved, [], "không được lưu token chưa kiểm tra")

    def test_save_emits_verified_config(self) -> None:
        from login_codex_9router.ui_models import ViotpConfig

        overlay = self._overlay()
        overlay.token.insert(0, "token-hop-le")
        overlay.verified = ViotpConfig("token-hop-le", "Tất cả nhà mạng", 50_000)
        overlay._save()
        self.assertEqual(len(self.saved), 1)
        self.assertEqual(self.saved[0].token, "token-hop-le")
        self.assertEqual(self.closed, 1, "lưu xong phải đóng modal")

    def test_clearing_token_marks_config_for_removal(self) -> None:
        from login_codex_9router.ui_models import ViotpConfig

        overlay = self._overlay(ViotpConfig("token-cu", "VIETTEL", None))
        overlay.token.delete(0, "end")
        overlay._token_changed()
        self.assertEqual(str(overlay.save_button.cget("state")), "normal")
        overlay._save()
        self.assertEqual(len(self.saved), 1)
        self.assertEqual(self.saved[0].token, "")

    def test_successful_check_enables_save_and_lists_networks(self) -> None:
        from login_codex_9router.integrations.viotp import Service

        overlay = self._overlay()
        overlay.token.insert(0, "token-hop-le")
        service = Service(1234, "OpenAI | ChatGPT", 3500)
        overlay.events.put(("ok", "token-hop-le", 50_000, ("VIETTEL", "MOBIFONE"), service, None))
        overlay._drain_events()
        self.assertEqual(str(overlay.save_button.cget("state")), "normal")
        self.assertIn("VIETTEL", overlay.network.cget("values"))
        self.assertIn("50.000", overlay.status.cget("text"))

    def test_service_label_shows_runtime_price(self) -> None:
        """Giá lấy từ API phải thay thế hằng số hiển thị (2.900đ)."""
        from login_codex_9router.integrations.viotp import Service

        overlay = self._overlay()
        overlay.token.insert(0, "token-hop-le")
        overlay.events.put(
            ("ok", "token-hop-le", 50_000, (), Service(1234, "OpenAI | ChatGPT", 3500), None)
        )
        overlay._drain_events()
        text = overlay.service_label.cget("text")
        self.assertIn("3.500đ", text)
        self.assertNotIn("2.900", text)
        self.assertNotIn("mặc định", text)

    def test_service_label_marks_fallback_when_lookup_fails(self) -> None:
        from login_codex_9router.integrations.viotp import OPENAI_SERVICE

        overlay = self._overlay()
        overlay.token.insert(0, "token-hop-le")
        overlay.events.put(
            ("ok", "token-hop-le", 50_000, (), OPENAI_SERVICE, "không tra được danh sách dịch vụ")
        )
        overlay._drain_events()
        text = overlay.service_label.cget("text")
        self.assertIn("mặc định", text)
        self.assertIn("không tra được", text)

    def test_response_for_stale_token_is_ignored(self) -> None:
        overlay = self._overlay()
        overlay.token.insert(0, "token-moi")
        # Kết quả của token cũ về muộn sau khi người dùng đã gõ token khác.
        overlay.events.put(("ok", "token-cu", 50_000, ("VIETTEL",), None, None))
        overlay._drain_events()
        self.assertIsNone(overlay.verified)
        self.assertEqual(str(overlay.save_button.cget("state")), "disabled")

    def test_overlay_is_inline_frame_not_extra_toplevel(self) -> None:
        """Modal phải nằm trong cửa sổ chính. Nếu là Toplevel, taskbar sẽ hiện thêm một
        cửa sổ phụ và người dùng có thể kéo nó ra khỏi cửa sổ cha."""
        before = self.root.winfo_children()
        overlay = self._overlay()
        self.assertIsInstance(overlay, tk.Widget)
        self.assertNotIsInstance(overlay, tk.Toplevel)
        new_toplevels = [
            child
            for child in self.root.winfo_children()
            if child not in before and isinstance(child, tk.Toplevel)
        ]
        self.assertEqual(new_toplevels, [], "không được tạo top-level window phụ")
        overlay.close()

    def test_token_entry_is_masked(self) -> None:
        overlay = self._overlay()
        self.assertEqual(overlay.token.cget("show"), "•")
        overlay._toggle_token()
        self.assertEqual(overlay.token.cget("show"), "")


if __name__ == "__main__":
    unittest.main()
