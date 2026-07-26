# Công việc cần làm

## P0 — Luồng cốt lõi

- [x] Sửa `ResponseObserver` để quan sát HTTP `401/403/429` ở bước submit email và password.
- [x] Thêm integration test cho chuỗi callback OAuth → điền callback → Connect → success/failure.
- [x] Kiểm tra callback bắt buộc có `code` hoặc xử lý tham số OAuth `error`.
- [ ] Chạy E2E được ủy quyền với 9router và tài khoản OpenAI thử nghiệm:
  - [ ] Dashboard login.
  - [ ] Mở OAuth popup và lấy `state`.
  - [ ] Đăng nhập email/password.
  - [ ] MFA/TOTP.
  - [ ] Nhận localhost callback.
  - [ ] Connect và xác nhận tài khoản xuất hiện trong 9router.

## P1 — VIOTP và xác minh điện thoại

> **CHẶN — mâu thuẫn spec, cần quyết định trước khi làm.**
> `docs/project-notes.md` cấm rõ ở hai chỗ: *"Không thuê số, không dùng số tạm và không tự
> động vượt bước xác minh"* và *"Không tích hợp API thuê số hoặc cơ chế dùng số tạm để vượt
> xác minh điện thoại"*. README cũng liệt kê điều này trong "Giới hạn hiện tại".
> Toàn bộ mục dưới đây đi ngược lại các dòng đó. Chọn một hướng rồi sửa tài liệu còn lại
> cho khớp; hiện tại luồng dừng ở `phone_verification_required` để xử lý thủ công.

6 mục dưới đây chỉ có ý nghĩa khi vượt xác minh điện thoại, nên vẫn để trống:

- [ ] Truyền `ViotpConfig` từ GUI vào `run_text()` và `run_account()`.
- [ ] Triển khai API thuê số VIOTP.
- [ ] Triển khai poll/lấy SMS OTP với timeout và cancellation.
- [ ] Tự động nhập số điện thoại và OTP vào OpenAI.
- [ ] Tiếp tục OAuth sau phone verification thành công.
- [ ] Xử lý lỗi hết số, thiếu số dư, OTP timeout và request bị hủy.
- [x] Xác minh service ID và giá VIOTP ở runtime thay vì chỉ dùng hằng số hiển thị.
      (`get_services()` + `resolve_openai_service()` gọi `/service/getv2`. Modal hiển thị giá
      thật sau khi kiểm tra token; tra hỏng hoặc mất id 1234 thì lùi về hằng số và ghi rõ
      "(mặc định — lý do)". Lỗi ở bước này không làm hỏng cả lần kiểm tra token.)
- [x] Thêm integration test cho toàn bộ luồng VIOTP bằng fixture.
      (`test_viotp.py` 6 → 14 test, phủ số dư, nhà mạng, dịch vụ, giá trả về dạng chuỗi,
      bỏ qua bản ghi hỏng, fallback, và che token trong thông báo lỗi.)
- [ ] Chạy smoke test với VIOTP thật bằng token được ủy quyền.
      **Cần bạn làm** — chỉ bạn có token. Mở **Cấu hình VIOTP** → **Kiểm tra kết nối**,
      đối chiếu giá hiện ra với giá thật trên VIOTP.

## P1 — Các nhánh đăng nhập

- [x] Thêm test cho retry `expired_otp` đúng một lần.
- [ ] Hỗ trợ hoặc báo rõ MFA input chia nhiều ô và trang chọn phương thức MFA.
- [x] Quyết định CAPTCHA sẽ dừng hay chờ người dùng xử lý thủ công.
      **Chọn: chờ.** Chế độ Hiển thị giữ cửa sổ Chrome mở, báo `waiting_manual`, chờ mặc định
      5 phút để bạn tự nhập số của mình và mã xác minh; qua được thì chạy tiếp. Chế độ Chạy ẩn
      dừng ngay vì không có cửa sổ để thao tác. Nút **Bỏ qua tài khoản đang chọn** hủy riêng
      một tài khoản. CLI có `--manual-timeout GIAY` (0 = dừng ngay như cũ).
      Ứng dụng vẫn không tự vượt bất kỳ bước xác minh nào.
- [x] Đồng bộ hành vi CAPTCHA giữa code và README.
      (README + dòng gợi ý trong GUI nay nói đúng: gặp CAPTCHA là dừng tài khoản và đóng
      Chrome ở **cả hai** chế độ. Nếu sau này đổi sang "chờ người dùng xử lý" thì phải
      sửa lại cả hai chỗ.)
- [ ] Thêm nhận diện luồng bắt buộc đổi mật khẩu/password reset.
- [ ] Quyết định phạm vi hỗ trợ dashboard OIDC-only; triển khai hoặc giữ giới hạn rõ ràng.
- [x] Thêm browser-flow tests cho `invalid_email`, account locked/disabled và rate limit.
      (`test_openai_error_flow.OpenAIErrorFlowTests` — 6 test, mỗi test khẳng định dừng
      sau đúng 1 lần submit, không retry.)

## P2 — GUI, CLI và lifecycle

- [x] Sửa summary GUI để phản ánh số tài khoản thành công/thất bại thay vì luôn báo `Hoàn tất`.
- [x] Thêm test GUI cho VIOTP overlay: lưu, hủy, Escape, focus/grab và đóng sau khi request kết thúc.
- [x] Thêm backdrop phủ cửa sổ khi mở VIOTP overlay nếu cần modal trực quan đầy đủ.
- [x] Thêm test Start/Stop và đóng GUI khi automation đang chạy.
- [x] Thêm timeout/fallback khi worker hoặc Playwright cleanup bị treo.
- [x] Xử lý `KeyboardInterrupt` và cancellation trong CLI.
- [x] Trả exit code khác `0` khi file có dòng account không hợp lệ hoặc không có account hợp lệ.
- [x] Thêm CLI subprocess tests cho env, encoding, output và exit code.

## P2 — Tài nguyên và độ ổn định

- [ ] Đặt giới hạn concurrency cấu hình được để tránh mở quá nhiều Chrome cùng lúc.
      **Mâu thuẫn spec:** `docs/project-notes.md` ghi "không đặt giới hạn worker hoặc yêu cầu
      cấu hình concurrency". Cần quyết định trước khi làm.
- [x] Test nhiều tài khoản gồm success, failure và cancellation đồng thời.
- [x] Xác minh browser/context luôn đóng khi lỗi, timeout hoặc callback treo.
- [x] Kiểm tra không lộ password, TOTP secret, OTP, token VIOTP, cookie hoặc OAuth code trong stdout/UI/error.

## P2 — Build và runtime

- [x] Build EXE mới từ HEAD hiện tại. (48.8 MB, 26/07 19:15 — bản cũ là từ 24/07.)
- [x] Smoke test EXE: mở GUI, mở/đóng VIOTP overlay bằng Escape và không tạo top-level window phụ.
      (EXE: đúng 1 top-level window. Escape + grab của overlay: `test_viotp_overlay.py`,
      trong đó có test khẳng định overlay là `ttk.Frame` chứ không phải `Toplevel`.)
- [x] Smoke test đóng EXE sạch và xác nhận tiến trình Chrome được dọn.
      (`WM_CLOSE` → cả bootloader lẫn tiến trình con thoát; số tiến trình Chrome không đổi.)
- [~] Xác minh EXE hoạt động trên máy chỉ có Google Chrome, không phụ thuộc source tree hoặc `.venv`.
      Đã chạy EXE với cwd `C:\Windows\Temp` (ngoài source tree) — GUI lên bình thường.
      **Còn lại cần bạn làm:** thử trên máy sạch không cài Python để loại trừ phụ thuộc ẩn.
- [x] Làm build thất bại hoặc cảnh báo rõ nếu browser integration tests bị skip.
      (`scripts/run-tests-strict.py` — chặn skip do thiếu Chrome/Playwright/Tkinter,
      vẫn cho phép skip E2E do thiếu biến môi trường. Gỡ bằng `ALLOW_SKIPPED_BROWSER_TESTS=1`.)

## P3 — Tài liệu

- [x] Sửa README về khả năng xử lý CAPTCHA thủ công cho đúng hành vi thực tế.
- [x] Đồng bộ mô tả `run.bat` với script cài đặt thực tế.
- [x] Đồng bộ README: build chạy cả unit và integration tests.
- [x] Cập nhật `docs/project-notes.md` với các trạng thái hiện có, gồm `cancelled` và lỗi auth cụ thể.
- [ ] Quyết định có cần tạo `docs/idea.md`; hiện ý tưởng nằm trong `docs/project-notes.md`.

## Tiêu chí hoàn tất

- [x] `python -m compileall src tests` thành công.
- [x] `python -m unittest discover -s tests -v` không lỗi và không skip kiểm thử browser bắt buộc.
      (89 test pass; skip duy nhất là `test_e2e_live` do thiếu biến môi trường E2E.)
- [x] Build EXE thành công từ mã nguồn hiện tại.
- [ ] Luồng E2E cốt lõi thành công bằng dữ liệu thử được ủy quyền.
- [x] Không ghi hoặc hiển thị dữ liệu nhạy cảm ngoài trường nhập được che.
      (Test tự động: `test_account_lifecycle.py` cho `AccountResult.detail` và `StatusUpdate`,
      `test_cli.py` cho stdout/stderr. Chưa phủ token VIOTP và OAuth code — cần E2E.)
