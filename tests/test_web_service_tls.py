import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.web_service import _build_https_redirect_location, _resolve_tls_settings


class TestResolveTlsSettings(unittest.TestCase):
    def test_returns_none_when_tls_not_configured(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(_resolve_tls_settings())

    def test_rejects_partial_tls_configuration(self):
        with mock.patch.dict("os.environ", {"TLS_CERT_FILE": "/tmp/cert.pem"}, clear=True):
            with self.assertRaisesRegex(ValueError, "must be set together"):
                _resolve_tls_settings()

    def test_rejects_redirect_without_tls_files(self):
        with mock.patch.dict("os.environ", {"TLS_ENABLE_HTTP_REDIRECT": "1"}, clear=True):
            with self.assertRaisesRegex(ValueError, "requires TLS_CERT_FILE"):
                _resolve_tls_settings()

    def test_rejects_invalid_redirect_port(self):
        with tempfile.TemporaryDirectory() as tmp:
            cert = Path(tmp) / "cert.pem"
            key = Path(tmp) / "key.pem"
            cert.write_text("dummy", encoding="utf-8")
            key.write_text("dummy", encoding="utf-8")

            with mock.patch.dict(
                "os.environ",
                {
                    "TLS_CERT_FILE": str(cert),
                    "TLS_KEY_FILE": str(key),
                    "TLS_ENABLE_HTTP_REDIRECT": "true",
                    "TLS_REDIRECT_HTTP_PORT": "70000",
                },
                clear=True,
            ):
                with self.assertRaisesRegex(ValueError, "1..65535"):
                    _resolve_tls_settings()

    def test_parses_valid_tls_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            cert = Path(tmp) / "cert.pem"
            key = Path(tmp) / "key.pem"
            cert.write_text("dummy", encoding="utf-8")
            key.write_text("dummy", encoding="utf-8")

            with mock.patch.dict(
                "os.environ",
                {
                    "TLS_CERT_FILE": str(cert),
                    "TLS_KEY_FILE": str(key),
                    "TLS_ENABLE_HTTP_REDIRECT": "yes",
                    "TLS_REDIRECT_HTTP_PORT": "8080",
                    "TLS_REDIRECT_HOST": "dev.geo.local",
                },
                clear=True,
            ):
                settings = _resolve_tls_settings()

        self.assertIsNotNone(settings)
        self.assertEqual(settings["cert_file"], str(cert))
        self.assertEqual(settings["key_file"], str(key))
        self.assertTrue(settings["redirect_enabled"])
        self.assertEqual(settings["redirect_http_port"], 8080)
        self.assertEqual(settings["redirect_host"], "dev.geo.local")


class TestHttpsRedirectLocation(unittest.TestCase):
    def test_uses_host_header_without_plain_http_port(self):
        location = _build_https_redirect_location(
            "/health?probe=1",
            host_header="127.0.0.1:8080",
            https_port=8443,
        )
        self.assertEqual(location, "https://127.0.0.1:8443/health?probe=1")

    def test_uses_explicit_host_override(self):
        location = _build_https_redirect_location(
            "/analyze",
            host_header="ignored.local:8080",
            https_port=443,
            explicit_host="api.dev.geo.local",
        )
        self.assertEqual(location, "https://api.dev.geo.local/analyze")


if __name__ == "__main__":
    unittest.main()
