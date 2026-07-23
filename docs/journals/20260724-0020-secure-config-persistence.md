---
title: "Secure Config Persistence Survived Real Validation"
date: "2026-07-24 00:20"
severity: medium
component: "Tk GUI configuration persistence"
status: resolved
---

# Secure Config Persistence Survived Real Validation

## Context

Tk GUI cần khôi phục HOST, chế độ Chrome, mật khẩu dashboard, token VIOTP và nhà mạng sau khi khởi động lại. File đích là `%LOCALAPPDATA%\login-codex-9router\config.json`; password và token là secret, không được ghi plaintext.

## What Happened

Feature lưu cấu hình JSON, bảo vệ `dashboard_password` và `viotp_token` bằng Windows DPAPI, rồi ghi atomically qua file tạm, `os.fsync()` và `os.replace()`. `load_config()` bắt lỗi JSON, UTF-8, schema và DPAPI, sau đó trả cấu hình mặc định kèm cảnh báo thay vì làm GUI lỗi lúc startup.

Validation gồm **40/40 tests pass**, compile pass và PyInstaller build pass. Smoke test Tk xác nhận persistence restore đủ năm giá trị, không lưu account input và không để plaintext secret trong JSON. Smoke corrupt-JSON xác nhận cảnh báo đúng một lần, lưu lại file hợp lệ và lần mở sau không cảnh báo.

## Reflection

Feature tưởng chỉ cần ghi vài field JSON nhưng chạm đồng thời vào secret handling, crash consistency, startup UX và binary packaging. Ghi trực tiếp có thể phá config nếu process dừng giữa write; lưu plaintext tạo credential leak trong `%LOCALAPPDATA%`. Unit test chưa đủ, vì DPAPI, Tk và PyInstaller đều cần bằng chứng runtime trên Windows.

## Decisions

- Dùng Windows DPAPI theo user hiện tại; không tự quản encryption key.
- Dùng atomic replace thay vì ghi đè file đích.
- Dùng toàn bộ cấu hình mặc định và cảnh báo một lần khi file không hợp lệ.
- Không persist account list, mật khẩu OpenAI, TOTP secret, OTP, cookie hoặc balance.
- Chấp nhận DPAPI chỉ bảo vệ at rest; process cùng Windows account hoặc administrator vẫn có thể giải mã.

## Next

- Giữ test corrupt JSON, DPAPI round-trip và atomic replacement trong regression suite.
- Chạy compile, full tests, PyInstaller build và GUI smoke trước mỗi release Windows.
- Chỉ bổ sung migration khi có schema version thứ hai; chỉ thêm file locking khi hỗ trợ nhiều instance cùng chỉnh cấu hình.
