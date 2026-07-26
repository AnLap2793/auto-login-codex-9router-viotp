# login-codex-9router

Ứng dụng Windows dùng Python, Tkinter và Playwright để kết nối nhiều tài khoản OpenAI Codex vào 9router. Mỗi tài khoản chạy trong một tiến trình Google Chrome riêng.

## Yêu cầu

- Windows 10/11.
- Python 3.11+ khi chạy từ source hoặc build.
- Google Chrome đã cài trên máy.
- Có mật khẩu dashboard nếu 9router bật đăng nhập bằng mật khẩu; OIDC-only không được tự động hóa.

## Chạy giao diện

### Cách 1: Nhanh nhất (Tự động)

Nhấp đúp `run.bat` trong thư mục dự án hoặc chạy từ Command Prompt / PowerShell:

```cmd
run.bat
```

Script tạo `.venv` nếu chưa có, chạy `pip install -e .` (kéo theo Playwright khai báo trong
`pyproject.toml`) rồi mở giao diện bằng `pythonw`. Script này **không** cài `requirements.txt`
và không chạy test — muốn cài đầy đủ cả PyInstaller thì dùng `build.bat`.

---

### Cách 2: Chạy trực tiếp bằng `py` (Không dùng `.venv`)

Cài đặt 1 lần duy nhất vào Python hệ thống:

```cmd
py -m pip install -r requirements.txt
py -m pip install -e .
```

Từ các lần sau, chạy trực tiếp bằng `py` hoặc `python`:

```cmd
py -m login_codex_9router.gui
```

---

### Cách 3: Chạy thủ công với môi trường ảo `.venv`

**Dùng Command Prompt / PowerShell:**

```cmd
# Lần đầu:
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\python.exe -m login_codex_9router.gui

# Các lần sau:
.venv\Scripts\python.exe -m login_codex_9router.gui
```

**Dùng Git Bash:**

```bash
# Lần đầu:
py -3.11 -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
python -m pip install -e .
python -m login_codex_9router.gui

# Các lần sau:
source .venv/Scripts/activate
python -m login_codex_9router.gui
```

### Sử dụng

1. Đảm bảo 9router đang chạy, sau đó nhập `9router HOST`, ví dụ `http://localhost:20127`.
2. Nhập mật khẩu dashboard nếu 9router bật đăng nhập. Mật khẩu được Windows DPAPI bảo vệ trước khi lưu.
3. Chọn chế độ Chrome:
   - **Hiển thị**: gặp CAPTCHA hoặc xác minh điện thoại thì ứng dụng **giữ cửa sổ Chrome mở
     và chờ bạn tự xử lý** (mặc định 5 phút). Xong thì tự chạy tiếp.
   - **Chạy ẩn**: không có cửa sổ để thao tác nên dừng ngay khi gặp các bước này.

   Ứng dụng không tự vượt CAPTCHA hay xác minh điện thoại: bạn nhập số của mình và mã xác minh
   bằng tay trong cửa sổ đó. Hết thời gian chờ thì tài khoản dừng với trạng thái
   `captcha_required` / `phone_verification_required`, các tài khoản khác không bị ảnh hưởng.
4. Nhấn **Cấu hình VIOTP** ở góc trên bên phải. Trong modal, nhập token rồi nhấn **Kiểm tra kết nối**; chọn một nhà mạng hoặc giữ **Tất cả nhà mạng**, sau đó nhấn **Lưu cấu hình**.
5. Header chỉ hiển thị trạng thái và số dư VIOTP. Dịch vụ mặc định là **OpenAI | ChatGPT** (`id=1234`, giá `2.900đ`). Token VIOTP được Windows DPAPI bảo vệ trước khi lưu.
6. Dán tài khoản hoặc nhấn **Chọn file .txt**. Mỗi tài khoản nằm trên một dòng:

```text
email|password|2fa_secret
```

7. Nhấn **Bắt đầu kết nối** và theo dõi bảng trạng thái. Nút **Dừng** hủy các task và đóng toàn bộ Chrome do ứng dụng mở.
8. Khi một dòng chuyển sang `waiting_manual`, mở cửa sổ Chrome của tài khoản đó và hoàn tất
   bước xác minh. Nếu muốn bỏ qua tài khoản này mà vẫn để các tài khoản khác chạy, chọn dòng
   đó rồi nhấn **Bỏ qua tài khoản đang chọn**.

Không commit file tài khoản. `.gitignore` loại trừ `accounts*.txt` và `credentials*.txt`.

### Lưu cấu hình

GUI tự khôi phục HOST, chế độ Chrome, mật khẩu dashboard, token VIOTP và nhà mạng từ:

```text
%LOCALAPPDATA%\login-codex-9router\config.json
```

Mật khẩu dashboard và token VIOTP được mã hóa bằng Windows DPAPI theo tài khoản Windows hiện tại trước khi ghi JSON. DPAPI ngăn đọc trực tiếp khi file bị sao chép sang tài khoản khác, nhưng tiến trình chạy dưới cùng tài khoản Windows hoặc administrator vẫn có thể giải mã. Secret vẫn tồn tại trong RAM khi ứng dụng sử dụng.

Ứng dụng không lưu danh sách tài khoản, mật khẩu OpenAI, TOTP secret, OTP, cookie hoặc số dư VIOTP. Nếu JSON hỏng hoặc không hợp lệ, GUI dùng cấu hình mặc định và cảnh báo một lần khi khởi động.

### Xử lý lỗi khởi động

Kiểm tra Python 3.11:

```bat
py -3.11 --version
```

Nếu `run.bat` không mở giao diện:

1. Xác nhận Python 3.11 và Google Chrome đã được cài.
2. Xác nhận dịch vụ 9router đang chạy tại HOST đã nhập.
3. Chạy các lệnh trong mục **Chạy thủ công** để xem thông báo lỗi.
4. Nếu môi trường cũ bị hỏng, xóa thư mục `.venv` rồi chạy lại `run.bat`.

## Cấu trúc dự án

```text
src/login_codex_9router/   Mã nguồn ứng dụng
├── auth/                  Luồng đăng nhập, lỗi, selector và TOTP
└── integrations/          OAuth callback và VIOTP
tests/unit/                Test logic thuần
tests/integration/         Test HTTP, Chrome và tích hợp
scripts/                   Script chạy GUI và build EXE
docs/                      Tài liệu dự án và API
```

## Build EXE

Nhấp đúp `build.bat`. Script sẽ:

1. Tạo `.venv`.
2. Cài `requirements.txt` và `pip install -e .`.
3. Chạy `compileall` và **toàn bộ** test (`unittest discover -s tests`), gồm cả integration
   test dùng Chrome. Test fail thì build dừng.
4. Tạo `dist\login-codex-9router.exe` bằng PyInstaller.

EXE không bundle Chrome; máy chạy vẫn phải có Google Chrome.

## Chạy CLI bằng Git Bash

Sau khi kích hoạt `.venv`:

```bash
export NINE_ROUTER_HOST=http://localhost:20127
export NINE_ROUTER_PASSWORD=mat-khau-dashboard
python -m login_codex_9router accounts.txt

# Thêm --headless để chạy Chrome ẩn
python -m login_codex_9router accounts.txt --headless
```

## Trạng thái lỗi đăng nhập

Ứng dụng kết hợp thông báo UI và HTTP status để báo: `invalid_email`, `invalid_password`, `account_locked`, `account_disabled`, `rate_limited`, `invalid_otp`, `expired_otp` hoặc `login_rejected`.

- Sai mật khẩu, tài khoản khóa/vô hiệu hóa, rate limit và OTP sai: dừng ngay, không retry.
- OTP hết hạn: chờ chu kỳ TOTP mới và retry tối đa một lần.
- Không hiển thị hoặc log response body, password, TOTP secret, OTP, cookie hay token.

## Giới hạn hiện tại

- Không tự động vượt CAPTCHA hay xác minh điện thoại. Ở chế độ Hiển thị, ứng dụng chờ bạn tự
  xử lý trong cửa sổ Chrome; hết giờ hoặc chạy ẩn thì dừng và báo trạng thái.
- Cấu hình VIOTP hiện chỉ kiểm tra token, số dư và nhà mạng; chưa tự động thuê số hoặc lấy OTP điện thoại.
- Mã TOTP được tạo cục bộ theo RFC 6238; khóa 2FA không rời khỏi máy.
- Dashboard OIDC-only và luồng bắt buộc đổi mật khẩu cần xử lý thủ công.
- Giao diện OpenAI có thể thay đổi. Locator ưu tiên label, role và thuộc tính HTML ổn định.

Chỉ sử dụng với tài khoản được phép quản lý. Không dùng để né rate limit hoặc cơ chế chống lạm dụng.

## Kiểm tra thủ công

```bash
python -m compileall src tests
python -m unittest discover -s tests -v
```
