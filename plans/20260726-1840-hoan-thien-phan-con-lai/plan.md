# Hoàn thiện các phần còn lại

Ngày: 2026-07-26

## Kết quả audit

Đã đối chiếu `docs/project-notes.md` (spec) + `README.md` với code thực tế trong `src/`, `tests/`.

| # | Hạng mục | Trạng thái |
|---|----------|-----------|
| 1 | Parse `email\|password\|2fa_secret`, bỏ dòng trống, lỗi từng dòng | Xong |
| 2 | TOTP RFC 6238 cục bộ, chờ chu kỳ mới | Xong |
| 3 | Mỗi tài khoản 1 tiến trình Chrome, cô lập context, dọn dẹp `finally` | Xong |
| 4 | Phân loại lỗi đăng nhập (UI text + HTTP status) | Xong |
| 5 | Retry OTP hết hạn tối đa 1 lần | Xong |
| 6 | Dừng khi CAPTCHA / xác minh điện thoại | Xong |
| 7 | OAuth callback server + đối chiếu `state` | Xong |
| 8 | Config DPAPI, ghi atomic, fallback khi JSON hỏng | Xong |
| 9 | GUI Tkinter + modal VIOTP | Xong |
| 10 | VIOTP: kiểm tra token / số dư / nhà mạng | Xong |
| **11** | **`auth/automation.py` compile được** | **HỎNG — IndentationError** |
| **12** | **File > 200 dòng theo house rule** | **Chưa** |
| **13** | **`docs/` theo cấu trúc bắt buộc trong CLAUDE.md** | **Chưa** |
| **14** | **Cổng callback lấy từ `CallbackServer.port`** | **Hardcode 1455 ở 2 chỗ** |
| **15** | **Báo lỗi khi cổng 1455 bận** | **Bind trùng im lặng trên Windows** |
| **16** | **Test cho GUI** | **Không có test nào** |

## Ngoài phạm vi (có chủ đích)

**VIOTP tự động thuê số + lấy OTP điện thoại — KHÔNG triển khai.**

`docs/project-notes.md` ghi rõ ở 2 chỗ:
- Mục *Luồng xử lý* bước 6: "Không thuê số, không dùng số tạm và không tự động vượt bước xác minh."
- Mục *Yêu cầu an toàn*: "Không tích hợp API thuê số hoặc cơ chế dùng số tạm để vượt xác minh điện thoại."

Xác minh số điện thoại của OpenAI là cơ chế chống lạm dụng. Tự động vượt bằng SIM thuê đi ngược lại chính spec của dự án và dòng cuối README ("Không dùng để né rate limit hoặc cơ chế chống lạm dụng"). Giữ nguyên `phone_verification_required` để xử lý thủ công.

VIOTP vẫn giữ vai trò hiện tại: cấu hình + kiểm tra token/số dư/nhà mạng.

## Các phase

| Phase | Nội dung | Trạng thái |
|-------|----------|-----------|
| [01](phase-01-sua-loi-compile.md) | Sửa lỗi compile `automation.py` | Xong |
| [02](phase-02-modul-hoa-automation.md) | Module hóa `automation.py` và `gui.py` | Xong |
| [03](phase-03-bo-sung-docs.md) | Bổ sung `docs/` theo cấu trúc bắt buộc | Xong |
| [04](phase-04-cung-hoa-cong-callback.md) | Cứng hóa cổng callback 1455 | Xong (chưa đủ, xem Phase 06) |
| [05](phase-05-nhom-khong-can-quyet-dinh.md) | Nhóm việc không cần quyết định trong `TASK.md` | Xong |
| [06](phase-06-sua-loi-tu-code-review.md) | Sửa lỗi từ code review (1 nghiêm trọng, 3 cao) | Xong |

## Phụ thuộc

- Phase 01 chặn tất cả: 3 test module không import được cho tới khi sửa.
- Phase 02 dựa vào test xanh từ Phase 01 để xác minh refactor không đổi hành vi.
