# System Architecture — login-codex-9router

## Tổng quan

Ứng dụng desktop đơn tiến trình Python. GUI (Tkinter) hoặc CLI gọi chung `runner.run_text`, điều phối N worker async (asyncio.Task), mỗi worker mở một tiến trình Chrome (Playwright) riêng cho một tài khoản. Không có server/database — chỉ 1 file config JSON local và 1 HTTP server nội bộ tạm (OAuth callback).

## Sơ đồ luồng

```
GUI (gui.py) ──┐
               ├──> runner.run_text(text, host, ...)
CLI (__main__) ┘         │
                          ├─ parse_accounts (accounts.py)
                          ├─ CallbackServer (integrations/oauth_callback.py)  [1 instance dùng chung]
                          └─ với mỗi account hợp lệ: asyncio.create_task(run_one)
                                    │
                                    v
                          auth/automation.run_account
                            ├─ playwright.chromium.launch (channel="chrome", 1 browser/account)
                            ├─ dashboard_login.login_dashboard   (đăng nhập 9router nếu cần)
                            ├─ oauth_flow.open_oauth              (gọi API authorize, mở tab OAuth)
                            ├─ openai_login.complete_openai_login (email → password → TOTP)
                            ├─ callback_server.wait(state)        (chờ callback local HTTP)
                            ├─ oauth_flow.verify_callback         (kiểm tra code/error)
                            ├─ _attach_to_dashboard               (dán URL vào modal 9router)
                            └─ finally: đóng browser, hủy callback task, discard state
```

## Module và trách nhiệm

| Module | Trách nhiệm |
|---|---|
| `accounts.py` | Parse `email\|password\|2fa_secret`, `Account`/`ParseError` dataclass, `masked_email` cho log an toàn |
| `cancellation.py` | `CancellationToken` — cờ hủy dùng chung giữa thread GUI và task async |
| `config.py` | `AppConfig`, đọc/ghi `config.json`, mã hóa secret bằng Windows DPAPI, validate host/network |
| `runner.py` | `run_text` — điều phối song song toàn bộ tài khoản, gộp `StatusUpdate` qua callback |
| `ui_models.py` | `ViotpConfig`, `ResultStats`, `calculate_stats` cho GUI |
| `theme.py` | Bảng màu và style ttk dùng chung |
| `main_window_layout.py` | Dựng widget cửa sổ chính (không gắn logic) |
| `gui.py` | `Application` — gắn command vào widget, chạy automation trong thread nền, xử lý event queue |
| `viotp_dialog.py` | Modal cấu hình VIOTP (kiểm tra token, chọn nhà mạng) |
| `__main__.py` | CLI entrypoint, đọc biến môi trường `NINE_ROUTER_HOST`/`NINE_ROUTER_PASSWORD` |
| `auth/results.py` | `ResultCode` (StrEnum), `AccountResult`, `FlowStopped` — kiểu kết quả dùng chung toàn bộ luồng |
| `auth/dashboard_login.py` | Đăng nhập dashboard 9router bằng mật khẩu (bỏ qua nếu không ở `/login`) |
| `auth/oauth_flow.py` | Gọi `GET /api/oauth/codex/authorize` bằng cookie context, mở tab OAuth; `verify_callback` kiểm tra `code`/`error` |
| `auth/openai_login.py` | Vòng lặp điền email/password/OTP, phát hiện CAPTCHA/xác minh điện thoại, dừng luồng qua `FlowStopped` |
| `auth/automation.py` | `run_account` — ghép các bước trên, khởi chạy/đóng Chrome, đảm bảo cleanup trong `finally` |
| `auth/errors.py` | `AuthErrorCode` (StrEnum), pattern match text lỗi UI/HTTP → mã lỗi |
| `auth/response_observer.py` | Lắng nghe response network (chỉ host openai.com/auth0.com) để phát hiện lỗi qua HTTP status/JSON field |
| `auth/selectors.py` | Locator Playwright ưu tiên label/role; `blocker()` phát hiện CAPTCHA/phone |
| `auth/totp.py` | `generate_totp`/`fetch_token` — RFC 6238, chờ sang chu kỳ mới nếu mã sắp hết hạn |
| `integrations/oauth_callback.py` | `CallbackServer` — `ThreadingHTTPServer` cục bộ nhận callback OAuth theo `state`, cố định cổng 1455 |
| `integrations/viotp.py` | Client API VIOTP: `get_balance`, `get_networks`, che token trong lỗi |

## Luồng OAuth callback

1. `CallbackServer()` khởi tạo 1 lần cho cả phiên chạy trong `runner.run_text`, bind `127.0.0.1:1455`.
   Cổng 1455 là **bắt buộc** — OpenAI chỉ chấp nhận `redirect_uri` là `http://localhost:1455/auth/callback`
   cho OAuth client của Codex, không đổi được. `CallbackServer` cho tham số `port` chủ yếu để test
   (`port=0` → OS tự cấp). Giá trị thực tế đọc qua `self.port` và truyền xuyên suốt thay vì hardcode lại:
   - `oauth_flow.open_oauth(context, host, callback_server.port)` — dùng cổng này làm `redirect_uri`.
   - `openai_login.complete_openai_login(page, account, token, callback_server.port)` — dùng cổng này để nhận diện URL callback (`callback_prefix`) và dừng vòng lặp điền form sớm.
2. Mỗi account gọi `callback_server.expect(state)` trước khi tạo `asyncio.create_task(callback_server.wait(state))`.
3. `Handler.do_GET` trong `CallbackServer` chỉ chấp nhận path `/callback` hoặc `/auth/callback`, `state` nằm trong `_expected_states`, và có `code` hoặc `error`.
4. `oauth_flow.verify_callback(url)` kiểm tra lại `error`/`code` trước khi dán vào modal 9router.
5. `finally` trong `run_account` luôn hủy `callback_task` và `discard(state)`, tránh rò rỉ state giữa các account chạy song song.

### Vì sao cổng callback phải bind độc quyền

`ThreadingHTTPServer` mặc định bật `SO_REUSEADDR`. Trên Windows, cờ này cho phép tiến trình
khác bind đè lên cổng đang dùng, và **bên bind sau là bên nhận kết nối**. Với cổng 1455,
hệ quả là mã ủy quyền OAuth có thể bị giao cho tiến trình khác mà không có lỗi nào được báo —
tài khoản chỉ treo tới hết timeout 300s.

`_ExclusiveHTTPServer` đặt `allow_reuse_address = False` và bật `SO_EXCLUSIVEADDRUSE`, biến
lệnh bind thành nguồn xác thực duy nhất về việc cổng còn trống. `_is_port_taken()` chỉ dùng để
báo lỗi sớm cho dễ hiểu, không phải hàng rào an toàn: nó không phát hiện được socket đã bind
mà chưa `listen`. Cổng bận → `PortBusyError` → `CallbackPortBusyError`, CLI thoát mã 2.

## Mô hình đồng thời

- 1 Chrome process / 1 tài khoản — `browser = await playwright.chromium.launch(...)` bên trong mỗi `run_account`.
- `runner.run_text` tạo N `asyncio.Task` (N = số account hợp lệ), không giới hạn số worker, không cấu hình concurrency.
- Toàn bộ N task chia sẻ 1 `CallbackServer` (1 HTTP server, nhiều `state` độc lập) và 1 `Playwright` instance (`async with async_playwright()`), nhưng mỗi task có `BrowserContext` riêng nên cookie/session cô lập hoàn toàn.
- Hủy (Stop): `CancellationToken.cancel()` set một `threading.Event` dùng chung; các bước dài trong `dashboard_login`/`openai_login`/`automation` gọi `token.raise_if_cancelled()` định kỳ để thoát sớm bằng `asyncio.CancelledError`.
- GUI chạy toàn bộ `asyncio.run(run_text(...))` trong 1 `threading.Thread` riêng (`_run_worker` ở `gui.py`) để không block main loop Tkinter; giao tiếp qua `queue.Queue` (`StatusUpdate` hoặc tuple lệnh) và `root.after(100, self._drain_events)`.

## Xử lý lỗi & phân loại

`auth/errors.classify_text` match chuỗi lỗi hiển thị trên UI (regex/keyword tiếng Anh của OpenAI); `auth/response_observer.ResponseObserver` song song lắng nghe response HTTP (chỉ host `openai.com`/`auth0.com`, field `code`/`type`/`message`) để bắt lỗi không hiển thị UI kịp. Cả 2 nguồn hội tụ về `AuthErrorCode` → raise `FlowStopped(ResultCode(...), message)`, được `run_account` bắt và trả về `AccountResult`.
