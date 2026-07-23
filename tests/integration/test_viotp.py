import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from login_codex_9router.integrations.viotp import OPENAI_SERVICE, ViotpError, get_balance, get_networks


class _Handler(BaseHTTPRequestHandler):
    routes: dict[str, object] = {}
    queries: list[dict[str, list[str]]] = []
    headers_seen: list[dict[str, str]] = []

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        self.queries.append(parse_qs(parsed.query))
        self.headers_seen.append({"Accept": self.headers.get("Accept", ""), "User-Agent": self.headers.get("User-Agent", "")})
        payload = self.routes.get(parsed.path, {"status_code": -1, "success": False})
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *args: object) -> None:
        pass


class ViotpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self) -> None:
        _Handler.routes = {}
        _Handler.queries = []
        _Handler.headers_seen = []

    def test_gets_balance_and_sends_token_as_query(self) -> None:
        _Handler.routes["/users/balance"] = {
            "status_code": 200,
            "success": True,
            "data": {"balance": 12345},
        }

        self.assertEqual(get_balance("secret token", base_url=self.base_url), 12345)
        self.assertEqual(_Handler.queries, [{"token": ["secret token"]}])
        self.assertEqual(_Handler.headers_seen[0]["Accept"], "application/json")
        self.assertEqual(_Handler.headers_seen[0]["User-Agent"], "login-codex-9router/0.1")

    def test_gets_networks(self) -> None:
        _Handler.routes["/networks/get"] = {
            "status_code": 200,
            "success": True,
            "data": [{"id": 1, "name": "MOBIFONE"}, {"id": 3, "name": "VIETTEL"}],
        }

        networks = get_networks("token", base_url=self.base_url)

        self.assertEqual([(item.id, item.name) for item in networks], [(1, "MOBIFONE"), (3, "VIETTEL")])

    def test_reports_invalid_token_without_exposing_it(self) -> None:
        _Handler.routes["/users/balance"] = {
            "status_code": 401,
            "success": False,
            "message": "bad secret-value",
        }

        with self.assertRaisesRegex(ViotpError, "token VIOTP không hợp lệ") as context:
            get_balance("secret-value", base_url=self.base_url)
        self.assertNotIn("secret-value", str(context.exception))

    def test_rejects_invalid_json_and_response_shapes(self) -> None:
        cases = [
            (b"not-json", "dữ liệu không hợp lệ"),
            ({"status_code": 200, "success": True, "data": {}}, "số dư hợp lệ"),
        ]
        for payload, message in cases:
            with self.subTest(message=message):
                _Handler.routes["/users/balance"] = payload
                with self.assertRaisesRegex(ViotpError, message):
                    get_balance("token", base_url=self.base_url)

    def test_reports_connection_error(self) -> None:
        with self.assertRaisesRegex(ViotpError, "không thể kết nối"):
            get_balance("token", base_url="http://127.0.0.1:1", timeout=0.1)

    def test_openai_service_defaults(self) -> None:
        self.assertEqual(
            (OPENAI_SERVICE.id, OPENAI_SERVICE.name, OPENAI_SERVICE.price),
            (1234, "OpenAI | ChatGPT", 2900),
        )


if __name__ == "__main__":
    unittest.main()
