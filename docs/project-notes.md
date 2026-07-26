# Ứng dụng tự động đăng nhập OpenAI trên 9router

## Công nghệ

- Python
- Playwright

## Mục tiêu

Tự động thêm tài khoản OpenAI vào 9router tại đường dẫn `/dashboard/providers/codex`.

## Dữ liệu đầu vào

Người dùng có thể nhập nhiều tài khoản. Mỗi tài khoản nằm trên một dòng theo định dạng:

```text
email|password|2fa_secret
```

Ví dụ:

```text
user-01@example.com|password-01|2fa-secret-01
user-02@example.com|password-02|2fa-secret-02
user-03@example.com|password-03|2fa-secret-03
```

Trong đó:

- `email`: địa chỉ email của tài khoản OpenAI.
- `password`: mật khẩu của tài khoản OpenAI.
- `2fa_secret`: khóa bí mật dùng để tạo mã TOTP 6 chữ số.
- Bỏ qua dòng trống; báo lỗi riêng cho dòng sai định dạng.
- Không để lỗi của một tài khoản làm dừng các tài khoản còn lại.

## Xử lý đồng thời

- Tạo một worker và khởi chạy một tiến trình Chrome riêng cho mỗi tài khoản trong dữ liệu đầu vào.
- Số tiến trình Chrome chạy đồng thời bằng số tài khoản hợp lệ; không đặt giới hạn worker hoặc yêu cầu cấu hình concurrency.
- Mỗi worker sở hữu một tiến trình Chrome và xử lý trọn vẹn một tài khoản, gồm đăng nhập và 2FA; xác minh điện thoại dừng để xử lý thủ công.
- Cookie, session và dữ liệu đăng nhập của từng tài khoản phải được cô lập hoàn toàn.
- Luôn đóng trang, context và tiến trình Chrome của tài khoản trong khối dọn dẹp, kể cả khi lỗi hoặc timeout.
- Mỗi tài khoản có timeout, retry có giới hạn và trạng thái độc lập.

Trạng thái vòng đời: `pending`, `running`, `waiting_manual`, `success`, `cancelled`.

`waiting_manual` là trạng thái tạm khi đang chờ người dùng tự xử lý CAPTCHA hoặc xác minh
điện thoại. Không tính là lỗi trong thống kê.

Trạng thái kết thúc do lỗi, dùng thay cho `failed` khi phân loại được nguyên nhân:

| Mã | Nghĩa |
|----|-------|
| `failed` | Lỗi không phân loại được, hoặc hết thời gian |
| `dashboard_auth_required` | 9router bật đăng nhập nhưng chưa nhập mật khẩu dashboard |
| `dashboard_auth_failed` | Sai mật khẩu dashboard, dashboard bị khóa, hoặc OIDC-only |
| `captcha_required` | Gặp CAPTCHA, dừng để xử lý thủ công |
| `phone_verification_required` | Gặp xác minh điện thoại, dừng để xử lý thủ công |
| `invalid_email` | Email hoặc tài khoản không tồn tại |
| `invalid_password` | Sai mật khẩu OpenAI |
| `account_locked` | Tài khoản bị khóa hoặc tạm ngưng |
| `account_disabled` | Tài khoản đã bị vô hiệu hóa |
| `rate_limited` | OpenAI giới hạn yêu cầu; không tự động thử lại |
| `invalid_otp` | Mã TOTP sai; kiểm tra lại khóa 2FA |
| `expired_otp` | Mã TOTP hết hạn cả hai lần thử |
| `login_rejected` | OpenAI từ chối đăng nhập (HTTP 401/403) |
- Kết quả phải giữ liên kết với số dòng đầu vào nhưng không ghi mật khẩu, khóa 2FA hoặc OTP vào log.
- Chỉ chạy đồng thời các tài khoản mà người dùng có quyền quản lý; không dùng đa luồng để né rate limit hoặc cơ chế chống lạm dụng.

## Luồng xử lý

1. Nhận và kiểm tra dữ liệu tài khoản đầu vào.
2. Mở 9router bằng Playwright với `HOST` do người dùng cấu hình.
3. Truy cập `/dashboard/providers/codex` và nhấn nút thêm tài khoản.
4. Thực hiện đăng nhập OpenAI bằng email và mật khẩu.
5. Khi OpenAI yêu cầu mã xác minh 2FA:
   - Tạo mã TOTP 6 chữ số cục bộ theo RFC 6238 từ `2fa_secret`.
   - Chờ sang chu kỳ mới nếu mã hiện tại sắp hết hạn.
   - Nhập mã vào trang xác minh; khóa 2FA không rời khỏi máy.
6. Khi OpenAI yêu cầu xác minh số điện thoại:
   - Không thuê số, không dùng số tạm và không tự động vượt bước xác minh.
   - Chế độ hiển thị: giữ cửa sổ Chrome mở, báo trạng thái `waiting_manual` và chờ người dùng
     tự nhập số của họ cùng mã xác minh. Qua được thì chạy tiếp; hết thời gian chờ thì báo
     `phone_verification_required`.
   - Chế độ chạy ẩn: không có cửa sổ để thao tác nên dừng ngay và báo `phone_verification_required`.
7. Khi CAPTCHA xuất hiện, xử lý y hệt bước 6 nhưng mã kết thúc là `captcha_required`.
   Ứng dụng không triển khai bất kỳ cơ chế tự vượt CAPTCHA nào.
8. Chờ 9router hoàn tất liên kết tài khoản và xác nhận kết quả.
9. Phân loại lỗi đăng nhập: email sai, mật khẩu sai, tài khoản khóa/vô hiệu hóa, rate limit, OTP sai hoặc hết hạn.
10. Chỉ retry OTP hết hạn tối đa một lần; các lỗi xác thực khác dừng ngay.
11. Ghi nhận trạng thái thành công, thất bại hoặc đã hủy; không lưu mật khẩu, khóa 2FA, OTP, cookie, token hay response body vào log.

## Yêu cầu an toàn

- Chỉ xử lý tài khoản và số điện thoại mà người dùng có quyền sử dụng.
- Không ghi thông tin đăng nhập, khóa 2FA, OTP hoặc API key vào log.
- Che dữ liệu nhạy cảm trong thông báo lỗi.
- Cấu hình `HOST` qua UI hoặc biến môi trường; GUI lưu HOST, chế độ Chrome và nhà mạng trong `%LOCALAPPDATA%\login-codex-9router\config.json`.
- Mật khẩu dashboard và token VIOTP được mã hóa bằng Windows DPAPI trước khi lưu; tiến trình cùng tài khoản Windows vẫn có thể giải mã và secret vẫn tồn tại trong RAM khi sử dụng.
- Không persist danh sách tài khoản, mật khẩu OpenAI, TOTP secret, OTP, cookie hoặc số dư VIOTP.
- Nếu JSON hỏng hoặc không hợp lệ, GUI dùng toàn bộ cấu hình mặc định và cảnh báo một lần khi khởi động.
- Dừng luồng khi CAPTCHA hoặc bước xác minh thủ công xuất hiện; không triển khai cơ chế vượt CAPTCHA.
- Không tích hợp API thuê số hoặc cơ chế dùng số tạm để vượt xác minh điện thoại.
