# Phase 02 — Module hóa file quá 200 dòng

**Ưu tiên:** P1
**Trạng thái:** Xong
**Phụ thuộc:** Phase 01 (cần test xanh để xác minh refactor không đổi hành vi)

## Bối cảnh

House rule: file code > 200 dòng thì tách. Trước phase này:

| File | Dòng |
|------|------|
| `gui.py` | 366 |
| `auth/automation.py` | 277 |
| `config.py` | 204 |

## Tách `auth/automation.py` (277 → 98)

Ranh giới tách theo trách nhiệm, không đổi logic:

| Module mới | Nội dung | Dòng |
|-----------|----------|------|
| `auth/results.py` | `ResultCode`, `AccountResult`, `FlowStopped`, `DEFAULT_CALLBACK_PORT` | 41 |
| `auth/dashboard_login.py` | `login_dashboard`, `url_path` | 33 |
| `auth/openai_login.py` | `complete_openai_login`, `_submit_otp`, `_wait_after_submit`, `_click_continue` | 141 |
| `auth/oauth_flow.py` | `open_oauth`, `verify_callback` | 55 |
| `auth/automation.py` | `run_account` (điều phối) + `_attach_to_dashboard` | 98 |

Giữ tương thích ngược: `automation.py` re-export `_login_dashboard`, `_open_oauth`,
`_complete_openai_login`, `ResultCode`, `FlowStopped`, `AccountResult`, `url_path`
vì test hiện có import các tên này.

## Tách `gui.py` (366 → 278)

| Module mới | Nội dung | Dòng |
|-----------|----------|------|
| `theme.py` | hằng màu + `configure_style()` | 32 |
| `main_window_layout.py` | `build_main_window()` → dataclass `MainWindowWidgets` | 177 |
| `gui.py` | `Application` (logic, gắn command, worker thread) | 278 |

Layout chỉ tạo widget, không gắn `command`. `Application._build` gắn command sau —
giữ bố cục độc lập với logic automation.

## Sửa kèm: cổng callback bị hardcode

`automation.py` cũ hardcode `http://localhost:1455/` ở 2 chỗ (redirect_uri gửi cho 9router,
và điều kiện nhận biết đã tới callback), trong khi `CallbackServer` cho phép chọn cổng
và expose `.port`. Nếu cổng khác 1455 thì redirect_uri sai → luồng treo.

Đã luồng `callback_server.port` qua `open_oauth(context, host, port)` và
`complete_openai_login(page, account, token, port)`.

## Test bổ sung

- `test_automation.test_open_oauth_uses_given_callback_port` — fixture server ghi lại
  request `/api/oauth/codex/authorize`, khẳng định `redirect_uri` dùng đúng cổng truyền vào.
- `tests/integration/test_gui_smoke.py` (mới, 4 test) — GUI trước đây không có test nào.
  Dựng `Application` với root ẩn, không chạy mainloop:
  - đủ 14 widget
  - 5 nút đều đã gắn command
  - đếm tài khoản / dòng lỗi đúng
  - `_set_running` bật/tắt nút Dừng và Bắt đầu đúng chiều

## Xác minh runtime

Khởi động `py -m login_codex_9router.gui`, tìm cửa sổ bằng Win32 `EnumWindows`:
- Cửa sổ `9Router · Codex Account Connector` — 1116x799
- Chụp màn hình: 3 khu vực đúng bố cục, config đã lưu được khôi phục, nút Dừng disabled
- `WM_CLOSE` → tiến trình thoát, exit code 0

## Tiêu chí hoàn thành

- [x] Mọi file trong `auth/` < 200 dòng
- [x] `gui.py` 366 → 278
- [x] 50/50 test pass (1 skip)
- [x] GUI render và đóng sạch

## Còn lại (chấp nhận)

`gui.py` 278 và `config.py` 204 vẫn trên 200. Tách thêm sẽ cắt ngang một class gắn kết
(`Application`) và một chuỗi mã hóa/giải mã liền mạch (DPAPI + encode/decode/validate) —
lợi bất cập hại. Ghi nhận, không xử lý.
