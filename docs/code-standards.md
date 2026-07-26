# Code Standards — login-codex-9router

Quy ước dưới đây phản ánh thực tế đang dùng trong repo (không phải lý tưởng hóa).

## Đặt tên

- Module: `snake_case.py` (`dashboard_login.py`, `oauth_flow.py`, `response_observer.py`).
- Package con theo domain: `auth/` (luồng đăng nhập), `integrations/` (dịch vụ ngoài: OAuth callback, VIOTP).
- Tên mô tả rõ trách nhiệm, không viết tắt tùy tiện (`openai_login.py` chứ không `oal.py`).

## Kiểu dữ liệu

- Dùng `@dataclass(frozen=True, slots=True)` cho toàn bộ value object bất biến: `Account`, `ParseError`, `AppConfig`, `AccountResult`, `ViotpConfig`, `ResultStats`, `Service`, `Network`, `AuthSignal` (xem `accounts.py`, `config.py`, `auth/results.py`, `ui_models.py`, `integrations/viotp.py`, `auth/errors.py`).
- `MainWindowWidgets` (`main_window_layout.py`) dùng `@dataclass(slots=True)` không `frozen` vì widget được gán 1 lần sau khi tạo.
- Mã trạng thái dùng `StrEnum`: `ResultCode` (`auth/results.py`), `AuthErrorCode` (`auth/errors.py`) — so sánh trực tiếp với string, serialize tự nhiên khi hiển thị lên UI/log.

## Giới hạn kích thước file

- Mục tiêu ~200 dòng/module. Đa số module tuân thủ (dài nhất trong `auth/` là `openai_login.py` ở 141 dòng).
- Khi vượt ngưỡng vì lý do hợp lý (state + event loop trong `gui.py` = 278 dòng; toàn bộ schema + DPAPI trong `config.py` = 204 dòng), tách phần độc lập ra module riêng thay vì rút gọn logic: `gui.py` đã tách `theme.py` (style) và `main_window_layout.py` (dựng widget); `auth/automation.py` (98 dòng) đã tách `dashboard_login.py`, `openai_login.py`, `oauth_flow.py`, `results.py` khỏi bản gộp cũ.

## Bảo mật / không log secret

- Không log/hiển thị mật khẩu, TOTP secret, OTP, cookie, token hay response body ở bất kỳ đâu.
- `Account.masked_email` che email trước khi đưa vào `StatusUpdate`/UI (`accounts.py`).
- Lỗi runtime chỉ báo `type(error).__name__`, không báo `str(error)` khi có khả năng chứa dữ liệu nhạy cảm (`auth/automation.run_account`, ngoại lệ chung).
- `integrations/viotp._get` che token trong message lỗi trả về (`message.replace(token, "***")`).
- `auth/response_observer.ResponseObserver` chỉ đọc field an toàn (`code`, `type`, `message`) từ response JSON, giới hạn độ dài 200 ký tự, chỉ inspect host `openai.com`/`auth0.com`.
- `config.py`: mật khẩu dashboard và token VIOTP luôn qua `_protect_secret`/`_unprotect_secret` (Windows DPAPI) trước khi ghi/đọc JSON.

## Thông báo lỗi tiếng Việt

- Toàn bộ message hiển thị cho người dùng (exception detail, `messagebox`, label GUI) viết tiếng Việt. Ví dụ: `"HOST phải là URL HTTP/HTTPS hợp lệ"` (`config.py`), `"cần xác minh số điện thoại thủ công"` (`auth/openai_login.py`).
- `auth/errors.MESSAGES` là tiếng Việt dù pattern match tiếng Anh (text lỗi gốc từ OpenAI UI).

## try/except quanh I/O

- Mọi thao tác file/network bọc trong `try/except` với danh sách exception cụ thể, không bắt `Exception` trần trừ khi cố ý (ví dụ tổng hợp lỗi runtime cuối cùng ở `run_account`).
- `config.load_config`/`save_config`: bắt `(ConfigError, json.JSONDecodeError, OSError, TypeError, UnicodeError)`.
- `integrations/viotp._get`: bắt riêng `HTTPError`, `(URLError, TimeoutError, OSError)`, `(json.JSONDecodeError, UnicodeDecodeError)` để phân loại thông báo.
- `gui.py` mọi handler UI (`_choose_file`, `_persist_app_config`, ...) bọc lỗi và hiển thị `messagebox` thay vì để exception rơi ra ngoài main loop Tkinter.

## Kiểm thử

- `tests/unit/`: test logic thuần (parse, config, TOTP, error classify) — không cần Chrome/network.
- `tests/integration/`: test HTTP server thật (`CallbackServer`), giả lập Playwright Page/Response, GUI smoke, và `test_e2e_live.py` (skip mặc định, cần Chrome + mạng thật).
- Chạy `python -m compileall src tests` trước khi test để bắt lỗi cú pháp sớm (dùng trong `scripts/build-exe.bat`).

## Async/concurrency

- `asyncio` cho toàn bộ luồng Playwright; `threading` chỉ dùng ở biên (GUI thread nền, `CancellationToken`, `ThreadingHTTPServer` của `CallbackServer`).
- Luôn `finally` dọn dẹp: đóng `browser`, hủy `callback_task`, `discard(state)` (`auth/automation.run_account`).
