from __future__ import annotations

import importlib.util
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit

import pytest


MODULE_PATH = Path("scripts/smoke/check_ui_login_start.py")


def _load_module():
    spec = importlib.util.spec_from_file_location("check_ui_login_start", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _StubHandler(BaseHTTPRequestHandler):
    # path -> (status_code, location)
    routes: dict[str, tuple[int, str | None]] = {
        "/login": (302, "/oidc/authorize?state=abc"),
    }

    def log_message(self, format, *args):  # noqa: A003
        return

    def do_GET(self):  # noqa: N802
        path = urlsplit(self.path).path
        status_code, location = self.routes.get(path, (404, ""))
        self.send_response(status_code)
        if location is not None:
            self.send_header("Location", location)
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
    _StubHandler.routes = {
        "/login": (302, "https://idp.example.test/oauth2/authorize?state=abc"),
    }

    with _StubServer() as stub:
        result = module.check_login_start(base_url=stub.base_url)

    assert result.ok is True
    assert result.reason == "ok"


def test_check_login_start_passes_for_ui_auth_login_hop_then_authorize_redirect():
    module = _load_module()
    _StubHandler.routes = {
        "/login": (302, "/auth/login?next=%2Fgui&reason=manual_login"),
        "/auth/login": (302, "https://idp.example.test/oauth2/authorize?state=abc"),
    }

    with _StubServer() as stub:
        result = module.check_login_start(base_url=stub.base_url)

    assert result.ok is True
    assert result.reason == "ok"


def test_check_login_start_fails_for_login_unavailable_fallback():
    module = _load_module()
    _StubHandler.routes = {
        "/login": (302, "/login?next=%2Fgui&reason=login_unavailable"),
    }

    with _StubServer() as stub:
        result = module.check_login_start(base_url=stub.base_url)

    assert result.ok is False
    assert result.reason == "login_unavailable_fallback"


def test_check_login_start_fails_for_non_redirect_status():
    module = _load_module()
    _StubHandler.routes = {
        "/login": (200, ""),
    }

    with _StubServer() as stub:
        result = module.check_login_start(base_url=stub.base_url)

    assert result.ok is False
    assert result.reason == "unexpected_status_200"


def test_check_login_start_fails_when_auth_login_hop_does_not_reach_authorize():
    module = _load_module()
    _StubHandler.routes = {
        "/login": (302, "/auth/login?next=%2Fgui"),
        "/auth/login": (302, "/login?next=%2Fgui&reason=manual_login"),
    }

    with _StubServer() as stub:
        result = module.check_login_start(base_url=stub.base_url)

    assert result.ok is False
    assert result.reason == "auth_login_hop_non_authorize_redirect"


def test_check_login_start_retries_transient_request_error(monkeypatch):
    module = _load_module()

    class _FakeResponse:
        status = 302

        def __init__(self, location: str) -> None:
            self.headers = {"Location": location}

        def getcode(self) -> int:
            return self.status

    class _FlakyOpener:
        def __init__(self) -> None:
            self.calls = 0

        def open(self, req, timeout):  # noqa: ARG002
            self.calls += 1
            if self.calls == 1:
                raise TimeoutError("timed out")
            return _FakeResponse("https://idp.example.test/oauth2/authorize?state=abc")

    opener = _FlakyOpener()
    monkeypatch.setattr(module, "build_opener", lambda *_args, **_kwargs: opener)

    result = module.check_login_start(
        base_url="https://www.dev.georanking.ch",
        max_attempts=2,
        retry_delay_seconds=0,
    )

    assert result.ok is True
    assert result.reason == "ok"
    assert opener.calls == 2


def test_check_login_start_retries_transient_http_502(monkeypatch):
    module = _load_module()

    class _FakeResponse:
        status = 302

        def __init__(self, location: str) -> None:
            self.headers = {"Location": location}

        def getcode(self) -> int:
            return self.status

    class _FlakyHttpErrorOpener:
        def __init__(self) -> None:
            self.calls = 0

        def open(self, req, timeout):  # noqa: ARG002
            self.calls += 1
            if self.calls == 1:
                raise HTTPError(req.full_url, 502, "Bad Gateway", {}, None)
            return _FakeResponse("https://idp.example.test/oauth2/authorize?state=abc")

    opener = _FlakyHttpErrorOpener()
    monkeypatch.setattr(module, "build_opener", lambda *_args, **_kwargs: opener)

    result = module.check_login_start(
        base_url="https://www.dev.georanking.ch",
        max_attempts=2,
        retry_delay_seconds=0,
    )

    assert result.ok is True
    assert result.reason == "ok"
    assert opener.calls == 2


def test_check_login_start_raises_when_retries_exhausted(monkeypatch):
    module = _load_module()

    class _AlwaysFailingOpener:
        def open(self, req, timeout):  # noqa: ARG002
            raise TimeoutError("timed out")

    monkeypatch.setattr(module, "build_opener", lambda *_args, **_kwargs: _AlwaysFailingOpener())

    with pytest.raises(RuntimeError, match="request_failed_after_retries"):
        module.check_login_start(
            base_url="https://www.dev.georanking.ch",
            max_attempts=2,
            retry_delay_seconds=0,
        )
