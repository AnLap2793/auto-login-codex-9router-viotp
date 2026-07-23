# Verify Windows UI

Xác minh runtime cho ứng dụng desktop này:

1. Build bằng `./build.bat` và kiểm tra `dist/login-codex-9router.exe` tồn tại.
2. Khởi động EXE ở background.
3. Dùng Win32 `EnumWindows` tìm title chứa `9Router`, ghi nhận kích thước cửa sổ.
4. Gửi `WM_CLOSE`, xác nhận cửa sổ biến mất và tiến trình thoát.
5. Không nhập tài khoản thật nếu chưa có dữ liệu thử được ủy quyền.
