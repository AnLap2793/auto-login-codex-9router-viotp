# Phase 06 — Sửa lỗi từ code review

**Ưu tiên:** P0/P1
**Trạng thái:** Xong

Review đối chiếu Phase 05 tìm ra 1 lỗi nghiêm trọng, 3 lỗi cao và một số lỗi vừa.
Đáng chú ý: bản vá cổng callback ở Phase 04 **chưa đóng được lỗ hổng**.

## C1 — Cướp cổng 1455 vẫn còn nguyên (bảo mật)

Phase 04 chỉ thêm probe "thử kết nối". Probe không đủ vì hai lý do:

1. Socket đã `bind` nhưng **chưa `listen`** thì probe không thấy → vẫn bind đè lên được.
2. `ThreadingHTTPServer` kế thừa `allow_reuse_address = 1`. Kể cả probe đúng, tiến trình khác
   vẫn bind được **sau** khi ta bind, và trên Windows bên bind sau là bên nhận kết nối.

Hậu quả: mã ủy quyền OAuth — một credential — bị giao cho tiến trình khác, `wait()` treo
300s mỗi tài khoản, không lỗi nào được báo.

**Sửa:** `_ExclusiveHTTPServer` với `allow_reuse_address = False` và `SO_EXCLUSIVEADDRUSE`.
Chính lệnh bind trở thành nguồn xác thực duy nhất; probe giữ lại chỉ để có thông báo đẹp.
Thêm `PortBusyError`.

Kiểm chứng bằng probe thủ công, cả 4 ca đều đúng:

| Ca | Kết quả |
|----|---------|
| Socket đã bind chưa listen | Bị chặn (trước đây lọt) |
| Hai `CallbackServer` cùng lúc | Bị chặn |
| Cổng trống | Bind bình thường |
| `port=0` | Vẫn tự chọn cổng |

## H1 — GUI kẹt vĩnh viễn ở trạng thái "đang chạy"

`_run_worker` bắt `except Exception`, nhưng `_set_running(False)` chỉ chạy ở nhánh
`done`/`error`. Worker chết vì `BaseException` (`CancelledError`, `SystemExit`) thì cả hai
nhánh đều bị bỏ qua → mọi ô nhập và nút disabled vĩnh viễn, bản `--windowed` không có stderr
nên người dùng không thấy gì. Chỉ khởi động lại app mới thoát.

**Sửa:** mở khóa ở nhánh `worker_stopped`, nhánh này luôn chạy.

## H2 — Backdrop VIOTP mồ côi làm liệt cửa sổ

Backdrop chỉ bị hủy bởi `_close_viotp` (callback `on_close`). Overlay chết mà không qua
`close()` sẽ để lại một frame `place(relwidth=1, relheight=1)` nằm trên toàn bộ nội dung,
nuốt mọi thao tác chuột. Mỗi lần mở lại chồng thêm một lớp.

**Sửa:** `_destroy_backdrop()` gọi ở đầu `_open_viotp`, và bọc `try/except` quanh phần
khởi tạo overlay.

## H3 — Lỗi dòng bị báo hai lần trên hai luồng

`main()` in ra stderr, rồi `run_text` parse lại và phát `StatusUpdate(status="failed")`
ra stdout. Bản stdout có định dạng **giống một dòng kết quả tài khoản**, nên script đọc
stdout sẽ đếm dòng sai định dạng thành tài khoản thất bại.

**Sửa:** CLI chỉ in lỗi dòng khi không còn tài khoản hợp lệ nào (lúc đó `run_text` không chạy).

## Các mục vừa

- **M1** `except RuntimeError` bắt nhầm `NotImplementedError`/`RecursionError` → thay bằng
  `CallbackPortBusyError` riêng. Cổng bận giờ trả exit **2** (không chạy được gì) thay vì 1.
- **M2** Ctrl+C lần hai thoát ngay (`os._exit`), phòng khi Chrome treo ở bước dọn dẹp.
  `signal.signal` bọc `try/except ValueError` cho trường hợp không phải main thread.
- **M3** `close_if_idle()` trả cổng lại nếu `__enter__` hỏng — nếu không, app tự chiếm 1455
  rồi tự báo "cổng bị chiếm, hãy đóng bản khác" mà không bao giờ thỏa mãn được.
- **M4** `run-tests-strict.py` đổi từ deny-list sang **allow-list**: chỉ skip E2E là hợp lệ,
  mọi skip khác chặn build. Deny-list bỏ lọt skip "cổng 1455 bận" và "Windows DPAPI required".
- **M5** `run_text` nhận `callback_port` (mặc định 1455); test dùng `0` để OS tự cấp cổng.
  Trước đó test đồng thời fail cứng khi 1455 bận.
- **L1** `AccountResult(account, "cancelled", …)` → `ResultCode.CANCELLED`.

## Tự kiểm điểm

Khi thêm test cho C1, tôi đặt lý do skip là `"thiếu E2E environment variables: cổng 1455 bận"`
để lọt allow-list — đúng kiểu false-negative mà M4 vừa cảnh báo, do chính tôi tạo ra.
Đã sửa thành `"cổng 1455 đang bị tiến trình khác giữ độc quyền"` để skip đó chặn build.

## Test bổ sung

97 test (Phase 05: 90). Thêm 7 test hồi quy:

- 3 test bind độc quyền: chặn socket bind-chưa-listen, chặn server thứ hai, cổng trả lại được sau khi đóng
- `test_worker_stopped_always_unlocks_ui`
- `test_orphaned_backdrop_is_cleared_on_reopen`, `test_backdrop_removed_when_overlay_construction_fails`
- `test_busy_callback_port_exits_bad_input_without_duplicate_line_errors`

## Chưa xử lý (ghi nhận)

- **M6** `stats.total` đếm cả dòng sai định dạng thành tài khoản, nên GUI hiện `1/2` còn CLI
  coi là 1 tài khoản. `calculate_stats` phân loại `failed` theo allow-list nên `ResultCode`
  mới thêm sẽ tự động bị xếp vào `failed`.
- **L6** `_drain_events` không bọc `try/finally`; một `TclError` sẽ giết vòng lặp sự kiện.
- **L8/L9** (có sẵn từ trước, không do phiên này tạo ra): `error_description` từ callback được
  in nguyên văn không giới hạn độ dài; `urllib` đi theo redirect và mang theo header `Cookie`
  của 9router, nên redirect sang host khác sẽ lộ session cookie.
