# Project Overview & PDR — login-codex-9router

## Mục tiêu

Ứng dụng Windows (Python + Tkinter + Playwright) tự động thêm nhiều tài khoản OpenAI Codex vào dashboard 9router tại `/dashboard/providers/codex`. Mỗi tài khoản chạy trong một tiến trình Google Chrome riêng, cô lập cookie/session.

## Phạm vi

- Nhập danh sách tài khoản (`email|password|2fa_secret`), chạy song song không giới hạn worker (bằng số tài khoản hợp lệ).
- Đăng nhập dashboard 9router bằng mật khẩu (nếu bật) — DPAPI bảo vệ khi lưu.
- Đăng nhập OpenAI: email → mật khẩu → TOTP 6 số (RFC 6238, sinh cục bộ từ `2fa_secret`).
- Nhận OAuth callback cục bộ (`CallbackServer`), dán URL vào modal 9router để hoàn tất liên kết.
- Phân loại lỗi đăng nhập theo `ResultCode`/`AuthErrorCode`, dừng ngay với hầu hết lỗi, chỉ retry OTP hết hạn tối đa 1 lần.
- Kiểm tra token/số dư/nhà mạng VIOTP (module `integrations/viotp.py`) hiển thị trên header GUI.
- Lưu cấu hình (HOST, chế độ Chrome, mật khẩu dashboard, token VIOTP, nhà mạng) tại `%LOCALAPPDATA%\login-codex-9router\config.json`, secret mã hóa bằng Windows DPAPI.
- CLI (`python -m login_codex_9router accounts.txt`) và GUI (`login_codex_9router.gui`) dùng chung `runner.run_text`.

## Người dùng

Người vận hành nội bộ quản lý nhiều tài khoản OpenAI được ủy quyền hợp pháp, cần gắn chúng vào 9router hàng loạt thay vì làm thủ công từng tài khoản.

## Dữ liệu vào / ra

**Vào:** file hoặc text dán trực tiếp, mỗi dòng `email|password|2fa_secret`; HOST 9router; mật khẩu dashboard (tùy chọn); token VIOTP (tùy chọn).

**Ra:** bảng trạng thái theo dòng — `pending`, `running`, rồi một trong các `ResultCode` (`success`, `failed`, `cancelled`, `dashboard_auth_required`, `dashboard_auth_failed`, `captcha_required`, `phone_verification_required`, `invalid_email`, `invalid_password`, `account_locked`, `account_disabled`, `rate_limited`, `invalid_otp`, `expired_otp`, `login_rejected`). Không ghi/log mật khẩu, khóa 2FA, OTP, cookie, token hay response body.

## Yêu cầu an toàn

- Chỉ xử lý tài khoản/số điện thoại mà người dùng có quyền quản lý; không dùng để né rate limit hay anti-abuse.
- Mật khẩu dashboard và token VIOTP mã hóa bằng Windows DPAPI (`CryptProtectData`/`CryptUnprotectData`) trước khi ghi JSON; process cùng tài khoản Windows hoặc admin vẫn giải mã được; secret tồn tại trong RAM khi dùng.
- Không persist danh sách tài khoản, mật khẩu OpenAI, TOTP secret, OTP, cookie hay số dư VIOTP.
- Dừng luồng (không tự động vượt) khi gặp CAPTCHA hoặc xác minh điện thoại.
- Config JSON hỏng/không hợp lệ → dùng mặc định, cảnh báo một lần khi khởi động.

## Ngoài phạm vi (chủ đích)

- **Tự động thuê số điện thoại / vượt xác minh số điện thoại**: bị cấm rõ trong `docs/project-notes.md` ("Không thuê số, không dùng số tạm..." và "Không tích hợp API thuê số..."). Khi OpenAI yêu cầu xác minh điện thoại, luồng dừng với `phone_verification_required` để người dùng xử lý thủ công. Đây là quyết định thiết kế có chủ đích, không phải phần chưa làm xong.
- Vượt CAPTCHA tự động.
- Dashboard OIDC-only hoặc luồng bắt buộc đổi mật khẩu — cần xử lý thủ công.
- Bundle Google Chrome trong bản build EXE (máy chạy phải tự cài Chrome).

## Tham khảo

- Spec gốc: `docs/project-notes.md`
- Hướng dẫn sử dụng chi tiết: `README.md`
