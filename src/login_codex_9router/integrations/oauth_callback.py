import asyncio
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit


class CallbackServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 1455) -> None:
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

        self._server = ThreadingHTTPServer((host, port), Handler)
        self.port = self._server.server_port
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self) -> "CallbackServer":
        self._thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)

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
