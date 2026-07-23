import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from login_codex_9router.config import (
    DEFAULT_CONFIG,
    DEFAULT_NETWORK,
    AppConfig,
    ConfigError,
    get_config_path,
    load_config,
    save_config,
)


class ConfigTests(unittest.TestCase):
    def test_uses_local_app_data_path(self) -> None:
        base = Path("C:/Users/test/AppData/Local")
        self.assertEqual(
            get_config_path(base),
            base / "login-codex-9router" / "config.json",
        )

    def test_missing_file_returns_defaults_without_warning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config, error = load_config(Path(directory) / "missing.json")
        self.assertEqual(config, DEFAULT_CONFIG)
        self.assertIsNone(error)

    @unittest.skipUnless(os.name == "nt", "Windows DPAPI required")
    def test_round_trip_encrypts_secrets_and_normalizes_host(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            expected = AppConfig(
                host="https://router.example/path",
                browser_mode="headless",
                dashboard_password="mật-khẩu-dashboard",
                viotp_token="viotp-token-bí-mật",
                viotp_network="VIETTEL",
            )
            saved = save_config(expected, path)
            raw = path.read_text(encoding="utf-8")
            loaded, error = load_config(path)

        self.assertEqual(saved.host, "https://router.example")
        self.assertEqual(loaded, saved)
        self.assertIsNone(error)
        self.assertNotIn(expected.dashboard_password, raw)
        self.assertNotIn(expected.viotp_token, raw)
        self.assertNotIn("2fa_secret", raw)

    def test_empty_secrets_are_serialized_as_null(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            save_config(DEFAULT_CONFIG, path)
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertIsNone(payload["dashboard_password_dpapi"])
        self.assertIsNone(payload["viotp"]["token_dpapi"])

    def test_invalid_json_returns_all_defaults_and_warning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text("{broken", encoding="utf-8")
            config, error = load_config(path)
        self.assertEqual(config, DEFAULT_CONFIG)
        self.assertIsNotNone(error)

    def test_invalid_utf8_returns_all_defaults_and_warning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_bytes(b"\xff\xfe")
            config, error = load_config(path)
        self.assertEqual(config, DEFAULT_CONFIG)
        self.assertIsNotNone(error)

    def test_invalid_schemas_return_defaults(self) -> None:
        valid = {
            "version": 1,
            "host": "http://localhost:20127",
            "browser_mode": "visible",
            "dashboard_password_dpapi": None,
            "viotp": {"token_dpapi": None, "network": DEFAULT_NETWORK},
        }
        invalid_payloads = (
            [],
            {**valid, "extra": True},
            {**valid, "version": 2},
            {**valid, "version": True},
            {**valid, "host": "file:///tmp/router"},
            {**valid, "browser_mode": "private"},
            {**valid, "viotp": []},
            {**valid, "viotp": {"token_dpapi": None, "network": ""}},
            {**valid, "dashboard_password_dpapi": "not base64!"},
            {**valid, "viotp": {"token_dpapi": None, "network": "VIETTEL"}},
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            for payload in invalid_payloads:
                with self.subTest(payload=payload):
                    path.write_text(json.dumps(payload), encoding="utf-8")
                    config, error = load_config(path)
                    self.assertEqual(config, DEFAULT_CONFIG)
                    self.assertIsNotNone(error)

    def test_invalid_config_does_not_replace_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            original = "existing-valid-data"
            path.write_text(original, encoding="utf-8")
            with self.assertRaises(ConfigError):
                save_config(AppConfig(host="invalid"), path)
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    @unittest.skipUnless(os.name == "nt", "Windows DPAPI required")
    def test_corrupted_dpapi_blob_returns_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            save_config(AppConfig(dashboard_password="secret"), path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["dashboard_password_dpapi"] = "AAAA"
            path.write_text(json.dumps(payload), encoding="utf-8")
            config, error = load_config(path)
        self.assertEqual(config, DEFAULT_CONFIG)
        self.assertIsNotNone(error)

    def test_replace_failure_keeps_existing_file_and_cleans_temp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text("existing-valid-data", encoding="utf-8")
            with patch("login_codex_9router.config.os.replace", side_effect=OSError("disk error")):
                with self.assertRaises(OSError):
                    save_config(DEFAULT_CONFIG, path)
            self.assertEqual(path.read_text(encoding="utf-8"), "existing-valid-data")
            self.assertEqual(tuple(path.parent.iterdir()), (path,))


if __name__ == "__main__":
    unittest.main()
