# Deployment Guide — login-codex-9router

## Yêu cầu môi trường

- Windows 10/11.
- Python 3.11+ (chạy từ source hoặc build).
- Google Chrome đã cài trên máy (Playwright dùng `channel="chrome"`, không bundle Chrome).
- Mật khẩu dashboard 9router nếu bật đăng nhập password; dashboard OIDC-only không tự động hóa được.

## Chạy từ source

### Cách 1: `run.bat` (tự động)

```cmd
run.bat
```

Gọi `scripts\run-gui.bat`: tự tạo `.venv`, cài `requirements.txt` + `pip install -e .`, mở GUI.

### Cách 2: `py` trực tiếp, không `.venv`

```cmd
py -m pip install -r requirements.txt
py -m pip install -e .
py -m login_codex_9router.gui
```

### Cách 3: `.venv` thủ công

```cmd
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\python.exe -m login_codex_9router.gui
```

Git Bash tương đương: `source .venv/Scripts/activate` rồi `python -m login_codex_9router.gui`.

### Chạy CLI

```bash
export NINE_ROUTER_HOST=http://localhost:20127
export NINE_ROUTER_PASSWORD=mat-khau-dashboard
python -m login_codex_9router accounts.txt
python -m login_codex_9router accounts.txt --headless
```

## Build EXE

```cmd
build.bat
```

Gọi `scripts\build-exe.bat`, thực hiện tuần tự:

1. Tạo `.venv` (Python 3.11) nếu chưa có.
2. `pip install -r requirements.txt` + `pip install -e .`.
3. `python -m compileall src tests`.
4. `python -m unittest discover -s tests -v` — build dừng nếu có test fail.
5. `pyinstaller --noconfirm --clean --onefile --windowed --name login-codex-9router --collect-all playwright scripts\gui_entry.py`.

Kết quả: `dist\login-codex-9router.exe`. Cấu hình PyInstaller chi tiết (datas/binaries/hiddenimports cho `playwright`) nằm ở `login-codex-9router.spec`, entrypoint là `scripts\gui_entry.py`.

**Lưu ý:** EXE không bundle Chrome — máy chạy EXE vẫn phải tự cài Google Chrome.

## Cấu hình lưu trữ

GUI tự lưu/khôi phục cấu hình tại:

```text
%LOCALAPPDATA%\login-codex-9router\config.json
```

Nội dung: `host`, `browser_mode`, `dashboard_password_dpapi`, `viotp.token_dpapi`, `viotp.network` (xem `src/login_codex_9router/config.py`). Mật khẩu dashboard và token VIOTP mã hóa bằng Windows DPAPI trước khi ghi — không sửa tay file này bằng cách chèn plaintext, `_decode` sẽ từ chối cấu trúc không đúng schema (`version`, `host`, `browser_mode`, `dashboard_password_dpapi`, `viotp` — đúng 5 key).

Nếu file hỏng/sai schema/sai version: GUI rơi về `DEFAULT_CONFIG` và hiện cảnh báo 1 lần khi khởi động, không crash.

## Kiểm tra thủ công

```bash
python -m compileall src tests
python -m unittest discover -s tests -v
```

Trạng thái hiện tại: 50 test pass, 1 skip (`tests/integration/test_e2e_live.py` — cần Chrome thật + mạng, không chạy trong CI/build mặc định).

## Xử lý lỗi khởi động

1. `py -3.11 --version` — xác nhận Python 3.11 có sẵn.
2. Xác nhận Google Chrome đã cài và dịch vụ 9router đang chạy tại HOST đã nhập.
3. Chạy tay các lệnh ở mục **Cách 3** để xem thông báo lỗi chi tiết.
4. Nếu `.venv` cũ hỏng: xóa thư mục `.venv` rồi chạy lại `run.bat`.

## Không commit

`.gitignore` loại trừ `accounts*.txt`, `credentials*.txt`, `.env`, `.venv/`, `dist/`, `build/`, `*.egg-info/`. Không commit file tài khoản hoặc bất kỳ secret nào.
