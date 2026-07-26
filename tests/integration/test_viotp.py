import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from login_codex_9router.integrations.viotp import (
    OPENAI_SERVICE,
    ViotpError,
    get_balance,
    get_networks,
    get_services,
    resolve_openai_service,
)


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

    def test_gets_services_and_sends_country(self) -> None:
        _Handler.routes["/service/getv2"] = {
            "status_code": 200,
            "success": True,
            "data": [{"id": 7, "name": "Facebook", "price": 800}, {"id": 1234, "name": "OpenAI", "price": 3500}],
        }

        services = get_services("token", base_url=self.base_url)

        self.assertEqual([(s.id, s.name, s.price) for s in services], [(7, "Facebook", 800), (1234, "OpenAI", 3500)])
        self.assertEqual(_Handler.queries[0]["country"], ["vn"])

    def test_accepts_price_returned_as_string(self) -> None:
        # Tài liệu VIOTP ghi price là số nhưng ví dụ trả về lại là chuỗi.
        _Handler.routes["/service/getv2"] = {
            "status_code": 200,
            "success": True,
            "data": [{"id": 1, "name": "Momo", "price": "350"}],
        }

        services = get_services("token", base_url=self.base_url)

        self.assertEqual(services[0].price, 350)

    def test_skips_malformed_service_entries(self) -> None:
        _Handler.routes["/service/getv2"] = {
            "status_code": 200,
            "success": True,
            "data": [
                {"id": "khong-phai-so", "name": "Xau", "price": 100},
                {"id": 5, "name": 123, "price": 100},
                {"id": 6, "name": "Thieu gia"},
                {"id": 9, "name": "Hop le", "price": 700},
            ],
        }

        services = get_services("token", base_url=self.base_url)

        self.assertEqual([(s.id, s.name, s.price) for s in services], [(9, "Hop le", 700)])

    def test_rejects_service_list_without_any_valid_entry(self) -> None:
        for payload in ({"status_code": 200, "success": True, "data": []},
                        {"status_code": 200, "success": True, "data": {"id": 1}}):
            with self.subTest(payload=payload):
                _Handler.routes["/service/getv2"] = payload
                with self.assertRaisesRegex(ViotpError, "danh sách dịch vụ"):
                    get_services("token", base_url=self.base_url)

    def test_resolves_openai_service_price_at_runtime(self) -> None:
        _Handler.routes["/service/getv2"] = {
            "status_code": 200,
            "success": True,
            "data": [{"id": 1234, "name": "OpenAI | ChatGPT", "price": 3500}],
        }

        service, warning = resolve_openai_service("token", base_url=self.base_url)

        self.assertEqual(service.price, 3500, "phải dùng giá từ API, không phải hằng số 2900")
        self.assertIsNone(warning)

    def test_falls_back_with_warning_when_service_id_missing(self) -> None:
        _Handler.routes["/service/getv2"] = {
            "status_code": 200,
            "success": True,
            "data": [{"id": 7, "name": "Facebook", "price": 800}],
        }

        service, warning = resolve_openai_service("token", base_url=self.base_url)

        self.assertEqual(service, OPENAI_SERVICE)
        self.assertIn("1234", warning)

    def test_falls_back_with_warning_when_lookup_fails(self) -> None:
        service, warning = resolve_openai_service("token", base_url="http://127.0.0.1:1", timeout=0.1)

        self.assertEqual(service, OPENAI_SERVICE)
        self.assertIn("không tra được", warning)

    def test_service_lookup_never_exposes_token(self) -> None:
        _Handler.routes["/service/getv2"] = {
            "status_code": -1,
            "success": False,
            "message": "loi voi secret-value",
        }

        _, warning = resolve_openai_service("secret-value", base_url=self.base_url)

        self.assertNotIn("secret-value", warning)


if __name__ == "__main__":
    unittest.main()
