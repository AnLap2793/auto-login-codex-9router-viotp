import asyncio
import errno
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit


class PortBusyError(OSError):
    """Cổng callback đã bị tiến trình khác giữ."""


class _ExclusiveHTTPServer(ThreadingHTTPServer):
    """Bind độc quyền cổng callback.

    `ThreadingHTTPServer` mặc định bật `SO_REUSEADDR`. Trên Windows, cờ này cho phép
    một tiến trình khác bind đè lên cổng đang dùng, và tiến trình bind sau là bên nhận
    kết nối. Với cổng 1455, hệ quả là mã ủy quyền OAuth có thể bị giao cho tiến trình khác
    mà không có lỗi nào được báo. Tắt `SO_REUSEADDR` và bật `SO_EXCLUSIVEADDRUSE` để
    lệnh bind trở thành nguồn xác thực duy nhất về việc cổng còn trống hay không.
    """

    allow_reuse_address = False

    def server_bind(self) -> None:
        exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
        if exclusive is not None:
            self.socket.setsockopt(socket.SOL_SOCKET, exclusive, 1)
        super().server_bind()


def _is_port_taken(host: str, port: int) -> bool:
    """Phát hiện sớm để báo lỗi rõ ràng. Không phải hàng rào an toàn — bind độc quyền
    trong `_ExclusiveHTTPServer` mới là thứ chặn thật, vì cổng có thể bị chiếm bởi socket
    đã bind mà chưa listen (khi đó hàm này trả về False)."""
    try:
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except OSError:
        return False


class CallbackServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 1455) -> None:
        if port and _is_port_taken(host, port):
            raise PortBusyError(errno.EADDRINUSE, f"cổng {port} đang được tiến trình khác sử dụng")
        self._callbacks: dict[str, str] = {}
        self._expected_states: set[str] = set()
        self._condition = threading.Condition()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parsed = urlsplit(self.path)
                params = parse_qs(parsed.query)
                state = params.get("state", [""])[0]
                with owner._condition:
                    valid = (
                        parsed.path in {"/callback", "/auth/callback"}
                        and state in owner._expected_states
                        and bool(params.get("code") or params.get("error"))
                    )
                    if valid:
                        owner._callbacks[state] = f"http://localhost:{owner.port}{self.path}"
                        owner._condition.notify_all()
                if not valid:
                    self.send_error(400, "Invalid OAuth callback")
                    return

                body = (
                    "<!doctype html><meta charset=utf-8>"
                    "<title>Authentication received</title>"
                    "<p>Authentication received. You may close this window.</p>"
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, _format: str, *args: object) -> None:
                pass

        try:
            self._server = _ExclusiveHTTPServer((host, port), Handler)
        except OSError as error:
            raise PortBusyError(
                getattr(error, "errno", errno.EADDRINUSE),
                f"không bind được cổng {port}: {error.strerror or error}",
            ) from error
        self.port = self._server.server_port
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self) -> "CallbackServer":
        self._thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)

    def close_if_idle(self) -> None:
        """Trả cổng lại khi server đã bind nhưng chưa từng phục vụ (thread chưa chạy).
        `__exit__` không chạy trong trường hợp này nên cần đóng socket thủ công."""
        if not self._thread.is_alive():
            self._server.server_close()

    def expect(self, state: str) -> None:
        with self._condition:
            self._expected_states.add(state)

    def discard(self, state: str) -> None:
        with self._condition:
            self._expected_states.discard(state)
            self._callbacks.pop(state, None)

    async def wait(self, state: str, timeout: float = 300) -> str:
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            with self._condition:
                callback_url = self._callbacks.pop(state, None)
            if callback_url:
                self.discard(state)
                return callback_url
            await asyncio.sleep(0.1)
        self.discard(state)
        raise TimeoutError("hết thời gian chờ OAuth callback")
