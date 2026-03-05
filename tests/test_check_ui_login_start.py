from __future__ import annotations

import importlib.util
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


MODULE_PATH = Path("scripts/smoke/check_ui_login_start.py")


def _load_module():
    spec = importlib.util.spec_from_file_location("check_ui_login_start", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _StubHandler(BaseHTTPRequestHandler):
    status_code = 302
    location = "/oidc/authorize?state=abc"

    def log_message(self, format, *args):  # noqa: A003
        return

    def do_GET(self):  # noqa: N802
        self.send_response(self.status_code)
        if self.location is not None:
            self.send_header("Location", self.location)
        self.send_header("Content-Length", "0")
        self.end_headers()


class _StubServer:
    def __init__(self) -> None:
        self.httpd = HTTPServer(("127.0.0.1", 0), _StubHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self.httpd.server_address
        return f"http://{host}:{port}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.httpd.shutdown()
        self.thread.join(timeout=2)
        self.httpd.server_close()


def test_check_login_start_passes_for_authorize_redirect():
    module = _load_module()
    _StubHandler.status_code = 302
    _StubHandler.location = "https://idp.example.test/oauth2/authorize?state=abc"

    with _StubServer() as stub:
        result = module.check_login_start(base_url=stub.base_url)

    assert result.ok is True
    assert result.reason == "ok"


def test_check_login_start_fails_for_login_unavailable_fallback():
    module = _load_module()
    _StubHandler.status_code = 302
    _StubHandler.location = "/login?next=%2Fgui&reason=login_unavailable"

    with _StubServer() as stub:
        result = module.check_login_start(base_url=stub.base_url)

    assert result.ok is False
    assert result.reason == "login_unavailable_fallback"


def test_check_login_start_fails_for_non_redirect_status():
    module = _load_module()
    _StubHandler.status_code = 200
    _StubHandler.location = ""

    with _StubServer() as stub:
        result = module.check_login_start(base_url=stub.base_url)

    assert result.ok is False
    assert result.reason == "unexpected_status_200"
