# Phase 04 — Cứng hóa cổng callback 1455

**Ưu tiên:** P1
**Trạng thái:** Xong

## Bối cảnh

Cổng 1455 do OpenAI quy định cho `redirect_uri` của Codex (`http://localhost:1455/auth/callback`).
Không thể đổi sang cổng khác — nếu cổng bận, luồng OAuth không hoàn tất được.

## Vấn đề phát hiện

`ThreadingHTTPServer` kế thừa `allow_reuse_address = 1`, tức bật `SO_REUSEADDR`.
Trên Windows, `SO_REUSEADDR` **cho phép hai socket cùng bind một cổng** (khác Linux).

Hệ quả: nếu Codex CLI hoặc một bản khác của ứng dụng đang giữ 1455, `CallbackServer()`
vẫn bind thành công. Callback OAuth khi đó về tay tiến trình nào là không xác định →
tài khoản treo tới khi hết timeout 300s, không có thông báo nào giải thích.

Đã xác nhận bằng test: bind sẵn 1455 rồi khởi tạo `CallbackServer()` — không hề lỗi.

## Cách sửa

Bind thành công không chứng minh cổng trống, nên kiểm tra bằng cách **thử kết nối**:

- `integrations/oauth_callback.py` — thêm `_is_port_taken(host, port)`; `CallbackServer.__init__`
  raise `OSError(EADDRINUSE)` nếu đã có tiến trình lắng nghe. Bỏ qua kiểm tra khi `port=0`
  (cổng tự chọn, dùng trong test).
- `runner.py` — bắt `OSError` khi tạo `CallbackServer`, đổi thành `RuntimeError` với hướng dẫn
  cụ thể: đóng bản khác của ứng dụng hoặc thoát Codex CLI rồi thử lại.

Không đụng tới `allow_reuse_address`: tắt nó sẽ khiến bind fail oan khi còn kết nối
ở trạng thái TIME_WAIT sau lần chạy trước.

## Test

`test_callback_server.test_busy_callback_port_reports_actionable_error` — chiếm 1455,
gọi `run_text`, khẳng định nhận `RuntimeError` có nhắc "1455". Skip nếu 1455 đã bị
tiến trình ngoài chiếm.

## Tiêu chí hoàn thành

- [x] Cổng bận → lỗi ngay lúc khởi động, không treo 300s
- [x] Thông báo nêu được cách xử lý
- [x] 51/51 test pass (1 skip)
