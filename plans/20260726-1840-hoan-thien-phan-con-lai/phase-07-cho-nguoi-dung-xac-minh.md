# Phase 07 — Chờ người dùng xác minh thủ công

**Ưu tiên:** P1
**Trạng thái:** Xong

Đóng mục `TASK.md`: *"Quyết định CAPTCHA sẽ dừng hay chờ người dùng xử lý thủ công"*.
**Quyết định: chờ.**

## Vấn đề

Trước phase này, `blocker()` phát hiện CAPTCHA hoặc xác minh điện thoại là `FlowStopped`
ngay lập tức, rồi `finally` đóng Chrome. Người dùng còn không kịp nhìn thấy màn hình,
nói gì tới xử lý. Tài khoản kẹt là kẹt luôn, phải làm lại thủ công ngoài ứng dụng.

## Giải pháp

Ứng dụng **không tự vượt** bước xác minh nào — nó chỉ giữ cửa sổ mở và đứng chờ.
Người dùng nhập số của chính họ và mã xác minh bằng tay.

| Chế độ | Hành vi |
|--------|---------|
| Hiển thị | Giữ Chrome mở, báo `waiting_manual`, chờ mặc định 300s, qua được thì chạy tiếp |
| Chạy ẩn | Dừng ngay như cũ — không có cửa sổ để thao tác |

Hết thời gian chờ → `phone_verification_required` / `captcha_required` như trước, kèm lý do
"hết thời gian chờ". Các tài khoản khác không bị ảnh hưởng.

## Thay đổi

**`cancellation.py`** — `CancellationToken` thành phân cấp. Token con cho từng tài khoản:
hủy con chỉ bỏ qua tài khoản đó, hủy cha (nút Dừng) thì mọi con đều coi như đã hủy.

**`auth/results.py`** — thêm `WAITING_MANUAL_STATUS`, `MANUAL_VERIFICATION_TIMEOUT`,
kiểu `ProgressCallback` để báo tiến độ giữa chừng lên UI.

**`auth/openai_login.py`** — `_wait_for_manual_resolution()` poll mỗi giây xem bước chặn
đã qua chưa, tôn trọng cancellation. Thời gian người dùng thao tác **không tính** vào hạn
đăng nhập 300s, nếu không thì chờ 5 phút sẽ ăn hết hạn.

**`runner.py`** — tạo token con mỗi tài khoản, trả về UI qua `on_account_start`.
Thêm tham số `manual_timeout`; ép về 0 khi `headless` bất kể cấu hình.

**`ui_models.py`** — `calculate_stats` thêm ô đếm `waiting`. Đây cũng là vá một phần
điểm M6 review đã nêu: trước đây mọi trạng thái lạ đều bị gộp vào `failed`, nên
`waiting_manual` sẽ bị đếm nhầm thành thất bại.

**GUI** — nút **Bỏ qua tài khoản đang chọn**, chỉ bật khi dòng đang chọn ở trạng thái
`running` hoặc `waiting_manual`. Thống kê hiện thêm "Chờ xác minh N" khi có.

**CLI** — cờ `--manual-timeout GIAY` (0 = dừng ngay như cũ).

## Test

119 test (trước: 107). Thêm 12:

- `test_manual_verification.py` (7): giải quyết được khi người dùng xử lý xong, báo đúng
  trạng thái `waiting_manual`, hết giờ thì bỏ cuộc, nút Bỏ qua hủy được, nút Dừng cũng hủy
  được qua token cha, chạy ẩn vẫn dừng ngay, thông báo hết giờ đúng
- `test_gui_smoke.py` (4): nút Bỏ qua chỉ bật cho tài khoản đang hoạt động, hủy đúng một
  tài khoản không đụng tài khoản khác, tắt khi không chạy, thống kê hiện ô chờ
- `test_ui_models.py` (1): `waiting_manual` không bị đếm là thất bại

## Tài liệu

README (3 chỗ), `docs/project-notes.md` (bước 6, 7 và bảng trạng thái), và dòng gợi ý
trong GUI — trước đó vẫn ghi "dừng ngay ở cả hai chế độ", nay đã sai.

## Ngoài phạm vi

Không triển khai thuê số VIOTP, poll SMS OTP hay tự điền số điện thoại. Xác minh điện thoại
là cơ chế chống lạm dụng; ứng dụng chỉ nhường quyền thao tác cho người dùng, không vượt hộ.
