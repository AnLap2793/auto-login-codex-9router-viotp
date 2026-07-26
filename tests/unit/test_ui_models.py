import unittest

from login_codex_9router.auth.results import WAITING_MANUAL_STATUS
from login_codex_9router.ui_models import ViotpConfig, calculate_stats


class UiModelsTests(unittest.TestCase):
    def test_viotp_summary_hides_token(self) -> None:
        config = ViotpConfig("secret-token", "VIETTEL", 125000)
        self.assertEqual(config.summary, "VIOTP: Đã kết nối · 125.000đ")
        self.assertNotIn(config.token, config.summary)

    def test_viotp_summary_marks_restored_config(self) -> None:
        config = ViotpConfig("secret-token", "VIETTEL", None)
        self.assertEqual(config.summary, "VIOTP: Đã lưu · VIETTEL")
        self.assertNotIn(config.token, config.summary)

    def test_calculates_result_stats(self) -> None:
        stats = calculate_stats(
            {
                1: "pending",
                2: "running",
                3: "success",
                4: "cancelled",
                5: "invalid_password",
                6: "failed",
            }
        )
        self.assertEqual(stats.total, 6)
        self.assertEqual(stats.running, 1)
        self.assertEqual(stats.success, 1)
        self.assertEqual(stats.cancelled, 1)
        self.assertEqual(stats.failed, 2)
        self.assertEqual(stats.waiting, 0)

    def test_waiting_is_not_counted_as_failure(self) -> None:
        """`waiting_manual` là trạng thái tạm, không phải lỗi — trước đây mọi trạng thái lạ
        đều bị gộp vào `failed`."""
        stats = calculate_stats({1: WAITING_MANUAL_STATUS, 2: "success", 3: "invalid_otp"})
        self.assertEqual(stats.waiting, 1)
        self.assertEqual(stats.failed, 1)
        self.assertEqual(stats.total, 3)


if __name__ == "__main__":
    unittest.main()
