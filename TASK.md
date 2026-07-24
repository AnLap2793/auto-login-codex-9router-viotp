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

- [ ] Truyền `ViotpConfig` từ GUI vào `run_text()` và `run_account()`.
- [ ] Triển khai API thuê số VIOTP.
- [ ] Triển khai poll/lấy SMS OTP với timeout và cancellation.
- [ ] Tự động nhập số điện thoại và OTP vào OpenAI.
- [ ] Tiếp tục OAuth sau phone verification thành công.
- [ ] Xử lý lỗi hết số, thiếu số dư, OTP timeout và request bị hủy.
- [ ] Xác minh service ID và giá VIOTP ở runtime thay vì chỉ dùng hằng số hiển thị.
- [ ] Thêm integration test cho toàn bộ luồng VIOTP bằng fixture.
- [ ] Chạy smoke test với VIOTP thật bằng token được ủy quyền.

## P1 — Các nhánh đăng nhập

- [ ] Thêm test cho retry `expired_otp` đúng một lần.
- [ ] Hỗ trợ hoặc báo rõ MFA input chia nhiều ô và trang chọn phương thức MFA.
- [ ] Quyết định CAPTCHA sẽ dừng hay chờ người dùng xử lý thủ công.
- [ ] Đồng bộ hành vi CAPTCHA giữa code và README.
- [ ] Thêm nhận diện luồng bắt buộc đổi mật khẩu/password reset.
- [ ] Quyết định phạm vi hỗ trợ dashboard OIDC-only; triển khai hoặc giữ giới hạn rõ ràng.
- [ ] Thêm browser-flow tests cho `invalid_email`, account locked/disabled và rate limit.

## P2 — GUI, CLI và lifecycle

- [ ] Sửa summary GUI để phản ánh số tài khoản thành công/thất bại thay vì luôn báo `Hoàn tất`.
- [ ] Thêm test GUI cho VIOTP overlay: lưu, hủy, Escape, focus/grab và đóng sau khi request kết thúc.
- [ ] Thêm backdrop phủ cửa sổ khi mở VIOTP overlay nếu cần modal trực quan đầy đủ.
- [ ] Thêm test Start/Stop và đóng GUI khi automation đang chạy.
- [ ] Thêm timeout/fallback khi worker hoặc Playwright cleanup bị treo.
- [ ] Xử lý `KeyboardInterrupt` và cancellation trong CLI.
- [ ] Trả exit code khác `0` khi file có dòng account không hợp lệ hoặc không có account hợp lệ.
- [ ] Thêm CLI subprocess tests cho env, encoding, output và exit code.

## P2 — Tài nguyên và độ ổn định

- [ ] Đặt giới hạn concurrency cấu hình được để tránh mở quá nhiều Chrome cùng lúc.
- [ ] Test nhiều tài khoản gồm success, failure và cancellation đồng thời.
- [ ] Xác minh browser/context luôn đóng khi lỗi, timeout hoặc callback treo.
- [ ] Kiểm tra không lộ password, TOTP secret, OTP, token VIOTP, cookie hoặc OAuth code trong stdout/UI/error.

## P2 — Build và runtime

- [ ] Build EXE mới từ HEAD hiện tại.
- [ ] Smoke test EXE: mở GUI, mở/đóng VIOTP overlay bằng Escape và không tạo top-level window phụ.
- [ ] Smoke test đóng EXE sạch và xác nhận tiến trình Chrome được dọn.
- [ ] Xác minh EXE hoạt động trên máy chỉ có Google Chrome, không phụ thuộc source tree hoặc `.venv`.
- [ ] Làm build thất bại hoặc cảnh báo rõ nếu browser integration tests bị skip.

## P3 — Tài liệu

- [ ] Sửa README về khả năng xử lý CAPTCHA thủ công cho đúng hành vi thực tế.
- [ ] Đồng bộ mô tả `run.bat` với script cài đặt thực tế.
- [ ] Đồng bộ README: build chạy cả unit và integration tests.
- [ ] Cập nhật `docs/project-notes.md` với các trạng thái hiện có, gồm `cancelled` và lỗi auth cụ thể.
- [ ] Quyết định có cần tạo `docs/idea.md`; hiện ý tưởng nằm trong `docs/project-notes.md`.

## Tiêu chí hoàn tất

- [ ] `python -m compileall src tests` thành công.
- [ ] `python -m unittest discover -s tests -v` không lỗi và không skip kiểm thử browser bắt buộc.
- [ ] Build EXE thành công từ mã nguồn hiện tại.
- [ ] Luồng E2E cốt lõi thành công bằng dữ liệu thử được ủy quyền.
- [ ] Không ghi hoặc hiển thị dữ liệu nhạy cảm ngoài trường nhập được che.
