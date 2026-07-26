# Phase 01 — Sửa lỗi compile `automation.py`

**Ưu tiên:** P0 (chặn toàn bộ dự án)
**Trạng thái:** Xong

## Bối cảnh

`src/login_codex_9router/auth/automation.py` có 10 dòng thừa ở cuối file (278–287): một mảnh
`finally` bị dán lặp lại sau khi hàm `url_path` đã kết thúc.

```
IndentationError: unexpected indent (automation.py, line 278)
```

## Ảnh hưởng

- `py -m compileall src tests` fail.
- Ứng dụng không chạy được — `runner.run_text` import `auth.automation` nên cả GUI lẫn CLI đều chết.
- 3 test module không import được: `test_automation`, `test_oauth_callback_flow`, `test_openai_error_flow`.
- Trước sửa: `Ran 39 tests — FAILED (errors=3, skipped=1)`.

## Nguyên nhân

Commit `ca968f3` dán trùng khối `finally` + `url_path`. Bản đúng đã có sẵn ở dòng 265–277,
bản thừa nằm sau đó không thuộc hàm nào.

## Các bước

1. Xóa dòng 278–287 (khối `with contextlib.suppress(...)` mồ côi và bản `url_path` trùng).
2. `py -m compileall -q src tests`.
3. `py -m unittest discover -s tests`.

## Tiêu chí hoàn thành

- [x] Compile sạch
- [x] 45/45 test pass (1 skip là `test_e2e_live`, cần môi trường thật)

## Kết quả

`Ran 45 tests — OK (skipped=1)`.
