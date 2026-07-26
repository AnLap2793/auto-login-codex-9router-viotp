# Project Roadmap — login-codex-9router

## Đã xong

- Parse danh sách tài khoản `email|password|2fa_secret`, validate email, báo lỗi theo dòng (`accounts.py`).
- Chạy song song 1 Chrome/tài khoản qua `runner.run_text` + `auth/automation.run_account`, cô lập cookie/context, dọn dẹp trong `finally`.
- Đăng nhập dashboard 9router bằng mật khẩu, phát hiện dashboard yêu cầu auth / auth thất bại (`auth/dashboard_login.py`).
- Đăng nhập OpenAI: email → mật khẩu → TOTP 6 số RFC 6238 (`auth/openai_login.py`, `auth/totp.py`), retry OTP hết hạn tối đa 1 lần.
- Phát hiện CAPTCHA và yêu cầu xác minh số điện thoại, dừng luồng đúng thiết kế (`auth/selectors.blocker`).
- Nhận OAuth callback qua HTTP server local ở cổng 1455 (cổng do OpenAI quy định, không đổi được).
  Giá trị cổng đọc từ `CallbackServer.port` và truyền qua `open_oauth`/`complete_openai_login`
  thay vì hardcode lại ở từng chỗ. Cổng bận → báo lỗi ngay kèm hướng xử lý
  (`integrations/oauth_callback.py`, `auth/oauth_flow.py`, `runner.py`).
- Phân loại lỗi đăng nhập theo `ResultCode`/`AuthErrorCode`, kết hợp UI text + response HTTP (`auth/errors.py`, `auth/response_observer.py`).
- GUI Tkinter: nhập HOST/mật khẩu/chế độ Chrome, dán/nạp file tài khoản, bảng trạng thái realtime, nút Dừng hủy toàn bộ task (`gui.py`, `main_window_layout.py`, `theme.py`).
- Modal cấu hình VIOTP: kiểm tra token, xem số dư, chọn nhà mạng (`viotp_dialog.py`, `integrations/viotp.py`).
- Lưu cấu hình bền vững tại `%LOCALAPPDATA%\login-codex-9router\config.json`, mã hóa secret bằng Windows DPAPI, tự phục hồi khi file hỏng (`config.py`).
- CLI thay thế GUI, dùng biến môi trường `NINE_ROUTER_HOST`/`NINE_ROUTER_PASSWORD` (`__main__.py`).
- Build EXE bằng PyInstaller qua `build.bat` (compile + unit test trước khi đóng gói).
- Refactor tách module: `auth/automation.py` cũ chia thành `results.py`, `dashboard_login.py`, `openai_login.py`, `oauth_flow.py`, `automation.py`; `gui.py` cũ chia thành `theme.py`, `main_window_layout.py`, `gui.py`.
- Test suite: 50 test pass, 1 skip (`tests/integration/test_e2e_live.py` — cần Chrome thật + mạng).

## Ngoài phạm vi có chủ đích

- **VIOTP tự động thuê số điện thoại**: không triển khai và sẽ không triển khai. `docs/project-notes.md` cấm rõ ("Không thuê số, không dùng số tạm...", "Không tích hợp API thuê số..."). Tích hợp VIOTP hiện tại chỉ dùng để kiểm tra token/số dư/nhà mạng, hiển thị thông tin cho người vận hành — không dùng để tự động lấy OTP điện thoại hay vượt bước xác minh. Khi OpenAI yêu cầu xác minh điện thoại, hệ thống dừng với `phone_verification_required` để xử lý thủ công. Đây là quyết định thiết kế cố định, không phải backlog.
- Vượt CAPTCHA tự động — không có kế hoạch, vi phạm yêu cầu an toàn trong spec.
- Xử lý dashboard OIDC-only hoặc luồng bắt buộc đổi mật khẩu tự động — vẫn cần thao tác thủ công.
- Bundle Chrome trong EXE.

## Rủi ro đang theo dõi

- Giao diện OpenAI có thể đổi selector — `auth/selectors.py` đã ưu tiên label/role/thuộc tính ổn định để giảm rủi ro, nhưng vẫn cần theo dõi khi OpenAI đổi UI.
- `gui.py` (278 dòng) và `config.py` (204 dòng) vượt nhẹ ngưỡng khuyến nghị 200 dòng/file — chấp nhận được vì đã tách phần độc lập ra module riêng (xem `docs/code-standards.md`).
