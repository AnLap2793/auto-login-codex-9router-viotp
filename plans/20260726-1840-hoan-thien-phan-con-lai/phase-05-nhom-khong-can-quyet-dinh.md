# Phase 05 — Nhóm việc không cần quyết định

**Ưu tiên:** P2/P3
**Trạng thái:** Xong (trừ build EXE đang chạy)

Các mục trong `TASK.md` làm được ngay, không vướng mâu thuẫn spec.
Loại trừ: khối VIOTP thuê số (P1), giới hạn concurrency, và các mục cần quyết hướng
(CAPTCHA dừng/chờ, OIDC-only, MFA nhiều ô, password reset, `docs/idea.md`).

## A. CLI — xong

- [x] Exit code khác 0 khi có dòng sai định dạng hoặc không có account hợp lệ
- [x] Xử lý `KeyboardInterrupt` qua `CancellationToken` để Chrome kịp đóng
- [x] `tests/integration/test_cli.py` — 8 subprocess test

Quy ước exit code:

| Code | Nghĩa |
|------|-------|
| 0 | Mọi dòng hợp lệ và mọi account thành công |
| 1 | Chạy được nhưng có dòng lỗi hoặc account thất bại |
| 2 | Không chạy được gì: file lỗi, HOST lỗi, không có account hợp lệ |
| 130 | Người dùng nhấn Ctrl+C |

Trước đây file toàn dòng sai vẫn thoát 0 vì `any()` trên list rỗng trả về False.

Ctrl+C không còn ném `KeyboardInterrupt` thẳng vào giữa `asyncio.run` — signal handler chỉ
bật cờ hủy để `run_text` đi qua đường dọn dẹp sẵn có và đóng Chrome.

## B. GUI — xong

- [x] Summary báo `Hoàn tất · thành công 2/4 · thất bại 1 · đã dừng 1` thay vì luôn "Hoàn tất"
- [x] Backdrop phủ cửa sổ khi mở VIOTP overlay (style `Overlay.TFrame` khai báo từ trước nhưng chưa dùng)
- [x] `_force_close` sau 30s nếu Playwright treo — worker chạy non-daemon nên chỉ destroy cửa sổ
      là chưa đủ, tiến trình vẫn sống thành process ma
- [x] `test_gui_smoke.py` 4 → 12 test: đóng GUI khi đang chạy, từ chối đóng, backdrop, summary
- [x] `tests/integration/test_viotp_overlay.py` — 8 test: Escape, grab, lưu, hủy, token chưa
      kiểm tra thì không lưu được, response của token cũ về muộn bị bỏ qua

## C. Test luồng auth — xong

- [x] `expired_otp` retry đúng một lần — 3 test trên `_submit_otp`: retry rồi thành công,
      hết hạn lần hai thì dừng không submit lần ba, lần đầu OK thì không retry
- [x] Browser-flow test cho `invalid_email`, `account_locked`, `account_disabled`, `rate_limited`
- [x] `tests/integration/test_account_lifecycle.py` — Chrome luôn đóng khi lỗi/timeout/hủy,
      nhiều tài khoản chạy song song giữ đúng số dòng, hủy giữa chừng
- [x] Test không lộ secret: password và TOTP secret không xuất hiện trong `AccountResult.detail`
      lẫn `StatusUpdate`; email bị che thành `fi***@example.com`

## D. Tài liệu — xong

- [x] README — chế độ "Hiển thị" **không** cho tự xử lý CAPTCHA; app dừng ngay rồi đóng Chrome
- [x] README — `run.bat` chỉ `pip install -e .`, không cài `requirements.txt`, không chạy test
- [x] README — build chạy **toàn bộ** test gồm integration, không chỉ unit test
- [x] `docs/project-notes.md` — bảng đầy đủ 13 mã trạng thái gồm `cancelled`

## E. Build

- [x] `scripts/run-tests-strict.py` — chặn build khi test bị skip do thiếu Chrome/Playwright/Tkinter,
      vẫn cho phép skip E2E do thiếu biến môi trường. Gỡ bằng `ALLOW_SKIPPED_BROWSER_TESTS=1`.
      `build-exe.bat` gọi script này thay cho `unittest discover`.
- [ ] Build lại EXE từ HEAD hiện tại (bản cũ trong `dist/` từ 24/07, không có bản sửa nào)

## Kết quả test

39 (đầu phiên, 3 lỗi import) → 51 → **89 test pass**, 1 skip là E2E cần tài khoản thật.

## Ngoài phạm vi đợt này

Smoke test EXE trên máy sạch và E2E với 9router thật: cần tài nguyên chỉ bạn có.
