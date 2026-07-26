# Codebase Summary

Nguồn: `./repomix-output.xml` (63 files, ~42.8K tokens). Cây thư mục và bảng dưới đây tổng hợp từ compaction đó, đối chiếu trực tiếp với source.

## Cây thư mục

```
login-codex-9router/
├── src/login_codex_9router/
│   ├── __main__.py             CLI entrypoint
│   ├── accounts.py             Parse account line
│   ├── cancellation.py         CancellationToken
│   ├── config.py               AppConfig + DPAPI persistence
│   ├── runner.py                Điều phối song song (run_text)
│   ├── ui_models.py             ViotpConfig, ResultStats
│   ├── theme.py                 Style ttk
│   ├── main_window_layout.py    Dựng widget GUI
│   ├── gui.py                   Logic Application (Tkinter)
│   ├── viotp_dialog.py          Modal cấu hình VIOTP
│   ├── auth/
│   │   ├── results.py           ResultCode, AccountResult, FlowStopped
│   │   ├── dashboard_login.py   Đăng nhập dashboard 9router
│   │   ├── oauth_flow.py        Authorize API + verify callback
│   │   ├── openai_login.py      Vòng lặp đăng nhập OpenAI (email/pass/OTP)
│   │   ├── automation.py        run_account (điều phối 1 tài khoản)
│   │   ├── errors.py             AuthErrorCode + classify
│   │   ├── response_observer.py  Theo dõi response HTTP
│   │   ├── selectors.py          Locator Playwright dùng chung
│   │   └── totp.py               RFC 6238 TOTP
│   └── integrations/
│       ├── oauth_callback.py     CallbackServer (HTTP local)
│       └── viotp.py              Client API VIOTP
├── tests/
│   ├── unit/                    Test logic thuần (không cần Chrome/network)
│   └── integration/             Test HTTP, Chrome, luồng OAuth, GUI smoke
├── scripts/                     gui_entry.py, build-exe.bat, run-gui.bat
├── docs/                        Tài liệu dự án (file này + các file khác)
├── login-codex-9router.spec     Cấu hình PyInstaller
├── build.bat / run.bat          Wrapper gọi script trong scripts/
├── requirements.txt             playwright, pyinstaller
└── pyproject.toml               Package config, entry points CLI/GUI
```

## Module → trách nhiệm → số dòng

| Module | Trách nhiệm | Dòng |
|---|---|---|
| `accounts.py` | Parse `email\|password\|2fa_secret`, mask email | 52 |
| `cancellation.py` | Cờ hủy dùng chung thread/async | 18 |
| `config.py` | Đọc/ghi config JSON, mã hóa DPAPI, validate | 204 |
| `runner.py` | Điều phối song song, gộp status | 88 |
| `ui_models.py` | Model thống kê + VIOTP cho GUI | 36 |
| `theme.py` | Style ttk | 31 |
| `main_window_layout.py` | Dựng widget cửa sổ chính | 177 |
| `gui.py` | Logic ứng dụng Tkinter | 278 |
| `viotp_dialog.py` | Modal cấu hình VIOTP | 175 |
| `__main__.py` | CLI entrypoint | 48 |
| `auth/results.py` | Mã trạng thái & kiểu kết quả chung | 41 |
| `auth/dashboard_login.py` | Đăng nhập dashboard 9router | 33 |
| `auth/oauth_flow.py` | Authorize API + verify callback | 55 |
| `auth/openai_login.py` | Vòng lặp đăng nhập OpenAI | 141 |
| `auth/automation.py` | Điều phối 1 tài khoản (run_account) | 98 |
| `auth/errors.py` | Phân loại lỗi text/HTTP | 73 |
| `auth/response_observer.py` | Theo dõi response HTTP nhạy cảm | 72 |
| `auth/selectors.py` | Locator Playwright dùng chung | 76 |
| `auth/totp.py` | Sinh mã TOTP RFC 6238 | 41 |
| `integrations/oauth_callback.py` | HTTP server nhận callback OAuth | 78 |
| `integrations/viotp.py` | Client API VIOTP | 82 |

**Tổng:** ~1900 dòng Python trong `src/`. Ghi chú: `gui.py` (278) và `config.py` (204) vượt ngưỡng khuyến nghị 200 dòng/file do gộp toàn bộ state + event loop (gui.py) và toàn bộ schema + DPAPI (config.py); đã tách phần dựng widget (`main_window_layout.py`) và style (`theme.py`) ra riêng để giảm tải.

## Test

| Thư mục | Vai trò | Số file | Dòng |
|---|---|---|---|
| `tests/unit/` | Test logic thuần, không cần Chrome/network | 7 file | ~312 |
| `tests/integration/` | Test HTTP local, Chrome giả lập, luồng OAuth, GUI smoke | 7 file | ~782 |

Chạy `python -m unittest discover -s tests -v`: 50 test pass, 1 skip (`test_e2e_live.py` — cần Chrome thật + mạng, bỏ qua mặc định).

## Cập nhật compaction

Chạy lại khi code đổi đáng kể:

```bash
npx --yes repomix --style xml -o repomix-output.xml
```
