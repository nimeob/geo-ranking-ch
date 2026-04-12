from __future__ import annotations

import importlib.util
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.error import HTTPError

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
    # request-target -> tuple(status_code, location) or rich dict
    routes: dict[str, object] = {
        "/login": (302, "/oidc/authorize?state=abc"),
    }

    def log_message(self, format, *args):  # noqa: A003
        return

    def _resolve_route(self) -> object:
        return self.routes.get(
            self.path, self.routes.get(self.path.split("?", 1)[0], (404, ""))
        )

    def do_GET(self):  # noqa: N802
        route = self._resolve_route()

        if isinstance(route, dict):
            status_code = int(route.get("status", 200))
            location = route.get("location")
            content_type = str(route.get("content_type", "text/html; charset=utf-8"))
            body = str(route.get("body", "")).encode("utf-8")
        else:
            status_code, location = route  # type: ignore[misc]
            content_type = "text/html; charset=utf-8"
            body = b""

        self.send_response(status_code)
        if location is not None:
            self.send_header("Location", str(location))
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)


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


def test_check_login_entry_passes_for_html_with_start_link():
    module = _load_module()
    _StubHandler.routes = {
        "/login?next=%2Fgui&reason=manual_login": {
            "status": 200,
            "body": '<a href="/login?next=%2Fgui&amp;reason=manual_login&amp;start=1">Jetzt anmelden</a>',
        },
    }

    with _StubServer() as stub:
        result = module.check_login_entry(base_url=stub.base_url)

    assert result.ok is True
    assert result.reason == "ok"


def test_check_login_entry_passes_for_html_with_query_encoded_next_path():
    module = _load_module()
    _StubHandler.routes = {
        "/login?next=%2Fjobs%3Fcity%3DZ%C3%BCrich%26sort%3Dscore&reason=manual_login": {
            "status": 200,
            "body": '<a href="/login?next=%2Fjobs%3Fcity%3DZ%C3%BCrich%26sort%3Dscore&amp;reason=manual_login&amp;start=1">Weiter</a>',
        },
    }

    with _StubServer() as stub:
        result = module.check_login_entry(
            base_url=stub.base_url, next_path="/jobs?city=Zürich&sort=score"
        )

    assert result.ok is True
    assert result.reason == "ok"


def test_check_login_entry_fails_when_html_start_link_has_wrong_next_path():
    module = _load_module()
    _StubHandler.routes = {
        "/login?next=%2Fgui&reason=manual_login": {
            "status": 200,
            "body": '<a href="/login?next=%2Fhistory&amp;reason=manual_login&amp;start=1">Jetzt anmelden</a>',
        },
    }

    with _StubServer() as stub:
        result = module.check_login_entry(base_url=stub.base_url)

    assert result.ok is False
    assert result.reason == "entry_start_link_next_mismatch"


def test_check_login_entry_fails_when_html_start_link_has_wrong_reason():
    module = _load_module()
    _StubHandler.routes = {
        "/login?next=%2Fgui&reason=manual_login": {
            "status": 200,
            "body": '<a href="/login?next=%2Fgui&amp;reason=manual_login_typo&amp;start=1">Jetzt anmelden</a>',
        },
    }

    with _StubServer() as stub:
        result = module.check_login_entry(base_url=stub.base_url)

    assert result.ok is False
    assert result.reason == "entry_start_link_reason_mismatch"


def test_check_login_entry_prefers_valid_start_link_when_multiple_links_exist():
    module = _load_module()
    _StubHandler.routes = {
        "/login?next=%2Fgui&reason=manual_login": {
            "status": 200,
            "body": (
                '<a href="/login?next=%2Fhistory&amp;reason=manual_login&amp;start=1">Falsch</a>'
                '<a href="/login?next=%2Fgui&amp;reason=manual_login&amp;start=1">Richtig</a>'
            ),
        },
    }

    with _StubServer() as stub:
        result = module.check_login_entry(base_url=stub.base_url)

    assert result.ok is True
    assert result.reason == "ok"


def test_check_login_entry_fails_when_html_start_link_uses_untrusted_absolute_host():
    module = _load_module()
    _StubHandler.routes = {
        "/login?next=%2Fgui&reason=manual_login": {
            "status": 200,
            "body": '<a href="https://evil.example.test/login?next=%2Fgui&amp;reason=manual_login&amp;start=1">Jetzt anmelden</a>',
        },
    }

    with _StubServer() as stub:
        result = module.check_login_entry(base_url=stub.base_url)

    assert result.ok is False
    assert result.reason == "entry_start_link_host_mismatch"


def test_check_login_entry_accepts_absolute_start_link_on_same_origin():
    module = _load_module()

    with _StubServer() as stub:
        _StubHandler.routes = {
            "/login?next=%2Fgui&reason=manual_login": {
                "status": 200,
                "body": (
                    f'<a href="{stub.base_url}/login?next=%2Fgui&amp;reason=manual_login&amp;start=1">'
                    "Jetzt anmelden"
                    "</a>"
                ),
            },
        }
        result = module.check_login_entry(base_url=stub.base_url)

    assert result.ok is True
    assert result.reason == "ok"


def test_same_origin_login_entry_href_rejects_scheme_or_port_mismatch():
    module = _load_module()

    request_url = "https://www.dev.georanking.ch/login?next=%2Fgui&reason=manual_login"
    assert (
        module._is_same_origin_login_entry_href(
            href="http://www.dev.georanking.ch/login?next=%2Fgui&reason=manual_login&start=1",
            request_url=request_url,
        )
        is False
    )
    assert (
        module._is_same_origin_login_entry_href(
            href="https://www.dev.georanking.ch:444/login?next=%2Fgui&reason=manual_login&start=1",
            request_url=request_url,
        )
        is False
    )


def test_check_login_entry_passes_for_authorize_redirect():
    module = _load_module()
    _StubHandler.routes = {
        "/login?next=%2Fgui&reason=manual_login": (
            302,
            "https://idp.example.test/oauth2/authorize?state=abc",
        ),
    }

    with _StubServer() as stub:
        result = module.check_login_entry(base_url=stub.base_url)

    assert result.ok is True
    assert result.reason == "ok_redirect"


def test_check_login_entry_rejects_non_authorize_path_even_when_query_mentions_authorize():
    module = _load_module()
    _StubHandler.routes = {
        "/login?next=%2Fgui&reason=manual_login": (
            302,
            "https://idp.example.test/login?next=%2Foauth2%2Fauthorize",
        ),
    }

    with _StubServer() as stub:
        result = module.check_login_entry(base_url=stub.base_url)

    assert result.ok is False
    assert result.reason == "entry_redirect_non_login_target"


def test_check_login_entry_rejects_authorize_redirect_when_expected_host_mismatches():
    module = _load_module()
    _StubHandler.routes = {
        "/login?next=%2Fgui&reason=manual_login": (
            302,
            "https://idp.example.test/oauth2/authorize?state=abc",
        ),
    }

    with _StubServer() as stub:
        result = module.check_login_entry(
            base_url=stub.base_url,
            allowed_authorize_hosts={"auth.dev.georanking.ch"},
        )

    assert result.ok is False
    assert result.reason == "entry_redirect_non_login_target"


def test_check_login_entry_accepts_authorize_redirect_when_expected_host_matches():
    module = _load_module()
    _StubHandler.routes = {
        "/login?next=%2Fgui&reason=manual_login": (
            302,
            "https://auth.dev.georanking.ch/oauth2/authorize?state=abc",
        ),
    }

    with _StubServer() as stub:
        result = module.check_login_entry(
            base_url=stub.base_url,
            allowed_authorize_hosts={"auth.dev.georanking.ch", "www.dev.georanking.ch"},
        )

    assert result.ok is True
    assert result.reason == "ok_redirect"


def test_check_login_entry_passes_for_http_307_auth_login_redirect():
    module = _load_module()
    _StubHandler.routes = {
        "/login?next=%2Fgui&reason=manual_login": (
            307,
            "/auth/login?next=%2Fgui&reason=manual_login",
        ),
    }

    with _StubServer() as stub:
        result = module.check_login_entry(base_url=stub.base_url)

    assert result.ok is True
    assert result.reason == "ok_redirect"


def test_check_login_entry_passes_for_auth_login_redirect():
    module = _load_module()
    _StubHandler.routes = {
        "/login?next=%2Fgui&reason=manual_login": (
            302,
            "/auth/login?next=%2Fgui&reason=manual_login",
        ),
    }

    with _StubServer() as stub:
        result = module.check_login_entry(base_url=stub.base_url)

    assert result.ok is True
    assert result.reason == "ok_redirect"


def test_check_login_entry_passes_for_single_canonical_login_hop_before_auth_login_redirect():
    module = _load_module()
    _StubHandler.routes = {
        "/login?next=%2Fgui&reason=manual_login": (
            307,
            "/login?next=%2Fgui&reason=manual_login&canonical=1",
        ),
        "/login?next=%2Fgui&reason=manual_login&canonical=1": (
            302,
            "/auth/login?next=%2Fgui&reason=manual_login",
        ),
    }

    with _StubServer() as stub:
        result = module.check_login_entry(base_url=stub.base_url)

    assert result.ok is True
    assert result.reason == "ok_redirect"
    assert "canonical=1" in result.request_url


def test_check_login_entry_passes_for_two_canonical_login_hops_before_auth_login_redirect():
    module = _load_module()
    _StubHandler.routes = {
        "/login?next=%2Fgui&reason=manual_login": (
            307,
            "/login?next=%2Fgui&reason=manual_login&canonical=1",
        ),
        "/login?next=%2Fgui&reason=manual_login&canonical=1": (
            307,
            "/login?next=%2Fgui&reason=manual_login&canonical=2",
        ),
        "/login?next=%2Fgui&reason=manual_login&canonical=2": (
            302,
            "/auth/login?next=%2Fgui&reason=manual_login",
        ),
    }

    with _StubServer() as stub:
        result = module.check_login_entry(base_url=stub.base_url)

    assert result.ok is True
    assert result.reason == "ok_redirect"
    assert "canonical=2" in result.request_url


def test_check_login_entry_fails_for_looping_same_login_redirect_chain():
    module = _load_module()
    _StubHandler.routes = {
        "/login?next=%2Fgui&reason=manual_login": (
            307,
            "/login?next=%2Fgui&reason=manual_login&canonical=1",
        ),
        "/login?next=%2Fgui&reason=manual_login&canonical=1": (
            307,
            "/login?next=%2Fgui&reason=manual_login&canonical=2",
        ),
        "/login?next=%2Fgui&reason=manual_login&canonical=2": (
            307,
            "/login?next=%2Fgui&reason=manual_login&canonical=1",
        ),
    }

    with _StubServer() as stub:
        result = module.check_login_entry(base_url=stub.base_url)

    assert result.ok is False
    assert result.reason == "entry_same_login_redirect_loop_detected"


def test_main_fails_with_entry_phase_when_login_entry_redirect_target_is_invalid(
    capsys,
):
    module = _load_module()
    _StubHandler.routes = {
        "/login?next=%2Fgui&reason=manual_login": (302, "/gui"),
    }

    with _StubServer() as stub:
        exit_code = module.main(["--base-url", stub.base_url])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["phase"] == "entry"
    assert payload["reason"] == "entry_redirect_non_login_target"


def test_main_accepts_json_out_alias_and_writes_result(tmp_path, capsys):
    module = _load_module()
    _StubHandler.routes = {
        "/login": (302, "https://idp.example.test/oauth2/authorize?state=abc"),
    }
    output_path = tmp_path / "login-start.json"

    with _StubServer() as stub:
        exit_code = module.main(
            ["--base-url", stub.base_url, "--json-out", str(output_path)]
        )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is True
    assert payload["request"]["base_url"] == stub.base_url
    assert payload["request"]["expected_authorize_host_source"] == "none"

    file_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert file_payload["ok"] is True
    assert file_payload["phase"] == "start"


def test_main_accepts_summary_json_alias_and_writes_result(tmp_path, capsys):
    module = _load_module()
    _StubHandler.routes = {
        "/login": (302, "https://idp.example.test/oauth2/authorize?state=abc"),
    }
    output_path = tmp_path / "login-start-summary.json"

    with _StubServer() as stub:
        exit_code = module.main(
            ["--base-url", stub.base_url, "--summary-json", str(output_path)]
        )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is True

    file_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert file_payload["ok"] is True
    assert file_payload["phase"] == "start"


def test_main_accepts_ui_base_url_alias(capsys):
    module = _load_module()
    _StubHandler.routes = {
        "/login": (302, "https://idp.example.test/oauth2/authorize?state=abc"),
    }

    with _StubServer() as stub:
        exit_code = module.main(["--ui-base-url", stub.base_url])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is True
    assert payload["request_url"].startswith(f"{stub.base_url}/login")
    assert payload["request"]["requested_base_url"] == stub.base_url
    assert payload["request"]["base_url_canonicalized"] is False


def test_main_accepts_json_flag_without_value(capsys):
    module = _load_module()
    _StubHandler.routes = {
        "/login": (302, "https://idp.example.test/oauth2/authorize?state=abc"),
    }

    with _StubServer() as stub:
        exit_code = module.main(["--base-url", stub.base_url, "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is True


def test_main_quiet_suppresses_stdout_but_still_writes_output_json(tmp_path, capsys):
    module = _load_module()
    _StubHandler.routes = {
        "/login": (302, "https://idp.example.test/oauth2/authorize?state=abc"),
    }
    output_path = tmp_path / "quiet-login-start.json"

    with _StubServer() as stub:
        exit_code = module.main(
            [
                "--base-url",
                stub.base_url,
                "--quiet",
                "--output-json",
                str(output_path),
            ]
        )

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == ""

    file_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert file_payload["ok"] is True
    assert file_payload["phase"] == "start"


def test_main_enforces_expected_authorize_host_allow_list(capsys):
    module = _load_module()
    _StubHandler.routes = {
        "/login": (302, "https://idp.example.test/oauth2/authorize?state=abc"),
    }

    with _StubServer() as stub:
        exit_code = module.main(
            [
                "--base-url",
                stub.base_url,
                "--expected-authorize-host",
                "auth.dev.georanking.ch,www.dev.georanking.ch",
            ]
        )

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is False
    assert payload["reason"] == "entry_redirect_non_login_target"
    assert payload["request"]["expected_authorize_host"] == sorted(
        {
            "auth.dev.georanking.ch",
            "auth.dev.geo-ranking.ch",
            "www.dev.georanking.ch",
            "www.dev.geo-ranking.ch",
        }
    )
    assert payload["request"]["expected_authorize_host_source"] == "argument"


def test_parse_allowed_authorize_hosts_normalizes_urls_ports_and_ipv6_literals():
    module = _load_module()

    hosts = module._parse_allowed_authorize_hosts(
        " https://AUTH.dev.georanking.ch/oauth2/authorize ,"
        "www.dev.georanking.ch:443,[2001:db8::1]:8443 "
    )

    assert hosts == {
        "auth.dev.georanking.ch",
        "auth.dev.geo-ranking.ch",
        "www.dev.georanking.ch",
        "www.dev.geo-ranking.ch",
        "2001:db8::1",
    }


def test_main_accepts_expected_authorize_host_values_with_urls_and_ports(capsys):
    module = _load_module()
    _StubHandler.routes = {
        "/login": (302, "https://auth.dev.georanking.ch/oauth2/authorize?state=abc"),
    }

    with _StubServer() as stub:
        exit_code = module.main(
            [
                "--base-url",
                stub.base_url,
                "--expected-authorize-host",
                "https://auth.dev.georanking.ch:443/oauth2/authorize,www.dev.georanking.ch:443",
            ]
        )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is True
    assert payload["phase"] == "start"


def test_parse_allowed_authorize_hosts_expands_geo_ranking_alias_to_georanking():
    module = _load_module()

    hosts = module._parse_allowed_authorize_hosts("auth.dev.geo-ranking.ch")

    assert hosts == {"auth.dev.geo-ranking.ch", "auth.dev.georanking.ch"}


def test_parse_allowed_authorize_hosts_expands_georanking_alias_to_geo_ranking():
    module = _load_module()

    hosts = module._parse_allowed_authorize_hosts("auth.dev.georanking.ch")

    assert hosts == {"auth.dev.georanking.ch", "auth.dev.geo-ranking.ch"}


def test_main_derives_default_expected_authorize_host_from_non_local_base_url(
    monkeypatch, capsys
):
    module = _load_module()

    captured: dict[str, set[str] | None] = {}

    def _fake_entry(**kwargs):
        captured["entry"] = kwargs.get("allowed_authorize_hosts")
        return module.LoginEntryCheckResult(
            ok=True,
            status_code=302,
            location="https://auth.dev.georanking.ch/oauth2/authorize?state=abc",
            request_url="https://www.dev.georanking.ch/login?next=%2Fgui&reason=manual_login",
            content_type="",
            reason="ok_redirect",
        )

    def _fake_start(**kwargs):
        captured["start"] = kwargs.get("allowed_authorize_hosts")
        return module.LoginStartCheckResult(
            ok=True,
            status_code=302,
            location="https://auth.dev.georanking.ch/oauth2/authorize?state=abc",
            request_url="https://www.dev.georanking.ch/login?next=%2Fgui&reason=manual_login&start=1",
            reason="ok",
        )

    monkeypatch.setattr(module, "check_login_entry", _fake_entry)
    monkeypatch.setattr(module, "check_login_start", _fake_start)

    exit_code = module.main(["--base-url", "https://www.dev.georanking.ch"])

    assert exit_code == 0
    expected_hosts = {
        "auth.dev.georanking.ch",
        "auth.dev.geo-ranking.ch",
        "www.dev.georanking.ch",
        "www.dev.geo-ranking.ch",
    }
    assert captured["entry"] == expected_hosts
    assert captured["start"] == expected_hosts

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["request"]["expected_authorize_host"] == sorted(expected_hosts)
    assert payload["request"]["expected_authorize_host_source"] == "derived_default"


def test_main_strips_trailing_dot_from_base_url_before_checks(monkeypatch, capsys):
    module = _load_module()

    captured: dict[str, object] = {}

    def _fake_entry(**kwargs):
        captured["entry_base_url"] = kwargs.get("base_url")
        captured["entry_hosts"] = kwargs.get("allowed_authorize_hosts")
        return module.LoginEntryCheckResult(
            ok=True,
            status_code=302,
            location="https://auth.dev.georanking.ch/oauth2/authorize?state=abc",
            request_url="https://www.dev.georanking.ch/login?next=%2Fgui&reason=manual_login",
            content_type="",
            reason="ok_redirect",
        )

    def _fake_start(**kwargs):
        captured["start_base_url"] = kwargs.get("base_url")
        captured["start_hosts"] = kwargs.get("allowed_authorize_hosts")
        return module.LoginStartCheckResult(
            ok=True,
            status_code=302,
            location="https://auth.dev.georanking.ch/oauth2/authorize?state=abc",
            request_url="https://www.dev.georanking.ch/login?next=%2Fgui&reason=manual_login&start=1",
            reason="ok",
        )

    monkeypatch.setattr(module, "check_login_entry", _fake_entry)
    monkeypatch.setattr(module, "check_login_start", _fake_start)

    exit_code = module.main(["--base-url", "https://www.dev.georanking.ch."])

    assert exit_code == 0
    assert captured["entry_base_url"] == "https://www.dev.georanking.ch"
    assert captured["start_base_url"] == "https://www.dev.georanking.ch"
    expected_hosts = {
        "auth.dev.georanking.ch",
        "auth.dev.geo-ranking.ch",
        "www.dev.georanking.ch",
        "www.dev.geo-ranking.ch",
    }
    assert captured["entry_hosts"] == expected_hosts
    assert captured["start_hosts"] == expected_hosts

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["request"]["base_url"] == "https://www.dev.georanking.ch"
    assert payload["request"]["requested_base_url"] == "https://www.dev.georanking.ch."
    assert payload["request"]["base_url_canonicalized"] is True
    assert payload["request"]["expected_authorize_host"] == sorted(expected_hosts)


def test_main_derives_default_expected_authorize_host_from_non_www_origin(
    monkeypatch, capsys
):
    module = _load_module()

    captured: dict[str, set[str] | None] = {}

    def _fake_entry(**kwargs):
        captured["entry"] = kwargs.get("allowed_authorize_hosts")
        return module.LoginEntryCheckResult(
            ok=True,
            status_code=302,
            location="https://auth.staging.georanking.ch/oauth2/authorize?state=abc",
            request_url="https://staging.geo-ranking.ch/login?next=%2Fgui&reason=manual_login",
            content_type="",
            reason="ok_redirect",
        )

    def _fake_start(**kwargs):
        captured["start"] = kwargs.get("allowed_authorize_hosts")
        return module.LoginStartCheckResult(
            ok=True,
            status_code=302,
            location="https://auth.staging.georanking.ch/oauth2/authorize?state=abc",
            request_url="https://staging.geo-ranking.ch/login?next=%2Fgui&reason=manual_login&start=1",
            reason="ok",
        )

    monkeypatch.setattr(module, "check_login_entry", _fake_entry)
    monkeypatch.setattr(module, "check_login_start", _fake_start)

    exit_code = module.main(["--base-url", "https://staging.geo-ranking.ch"])

    assert exit_code == 0
    expected_hosts = {
        "auth.staging.georanking.ch",
        "auth.staging.geo-ranking.ch",
        "staging.georanking.ch",
        "staging.geo-ranking.ch",
    }
    assert captured["entry"] == expected_hosts
    assert captured["start"] == expected_hosts

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["request"]["expected_authorize_host"] == sorted(expected_hosts)
    assert payload["request"]["expected_authorize_host_source"] == "derived_default"


def test_main_canonicalizes_legacy_dev_non_www_base_url_before_checks(monkeypatch, capsys):
    module = _load_module()

    captured: dict[str, object] = {}

    def _fake_entry(**kwargs):
        captured["entry_base_url"] = kwargs.get("base_url")
        captured["entry_hosts"] = kwargs.get("allowed_authorize_hosts")
        return module.LoginEntryCheckResult(
            ok=True,
            status_code=302,
            location="https://auth.dev.georanking.ch/oauth2/authorize?state=abc",
            request_url="https://www.dev.geo-ranking.ch/login?next=%2Fgui&reason=manual_login",
            content_type="",
            reason="ok_redirect",
        )

    def _fake_start(**kwargs):
        captured["start_base_url"] = kwargs.get("base_url")
        captured["start_hosts"] = kwargs.get("allowed_authorize_hosts")
        return module.LoginStartCheckResult(
            ok=True,
            status_code=302,
            location="https://auth.dev.georanking.ch/oauth2/authorize?state=abc",
            request_url="https://www.dev.geo-ranking.ch/login?next=%2Fgui&reason=manual_login&start=1",
            reason="ok",
        )

    monkeypatch.setattr(module, "check_login_entry", _fake_entry)
    monkeypatch.setattr(module, "check_login_start", _fake_start)

    exit_code = module.main(["--base-url", "https://dev.geo-ranking.ch"])

    assert exit_code == 0
    assert captured["entry_base_url"] == "https://www.dev.geo-ranking.ch"
    assert captured["start_base_url"] == "https://www.dev.geo-ranking.ch"
    expected_hosts = {
        "auth.dev.georanking.ch",
        "auth.dev.geo-ranking.ch",
        "www.dev.georanking.ch",
        "www.dev.geo-ranking.ch",
    }
    assert captured["entry_hosts"] == expected_hosts
    assert captured["start_hosts"] == expected_hosts

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["request"]["base_url"] == "https://www.dev.geo-ranking.ch"
    assert payload["request"]["requested_base_url"] == "https://dev.geo-ranking.ch"
    assert payload["request"]["base_url_canonicalized"] is True
    assert payload["request"]["expected_authorize_host"] == sorted(expected_hosts)


def test_derive_default_expected_authorize_host_skips_local_and_ip_origins():
    module = _load_module()

    assert module._derive_default_allowed_authorize_hosts("http://localhost:5173") == set()
    assert (
        module._derive_default_allowed_authorize_hosts("http://localhost.localdomain:5173")
        == set()
    )
    assert module._derive_default_allowed_authorize_hosts("http://127.0.0.1:5173") == set()
    assert module._derive_default_allowed_authorize_hosts("http://[2001:db8::1]:5173") == set()


def test_main_accepts_geo_ranking_authorize_host_alias_for_georanking_redirect(capsys):
    module = _load_module()
    _StubHandler.routes = {
        "/login": (302, "https://auth.dev.georanking.ch/oauth2/authorize?state=abc"),
    }

    with _StubServer() as stub:
        exit_code = module.main(
            [
                "--base-url",
                stub.base_url,
                "--expected-authorize-host",
                "auth.dev.geo-ranking.ch",
            ]
        )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is True
    assert payload["phase"] == "start"


def test_check_login_start_passes_for_authorize_redirect():
    module = _load_module()
    _StubHandler.routes = {
        "/login": (302, "https://idp.example.test/oauth2/authorize?state=abc"),
    }

    with _StubServer() as stub:
        result = module.check_login_start(base_url=stub.base_url)

    assert result.ok is True
    assert result.reason == "ok"


def test_check_login_start_rejects_non_authorize_path_even_when_query_mentions_authorize():
    module = _load_module()
    _StubHandler.routes = {
        "/login": (302, "https://idp.example.test/login?next=%2Foauth2%2Fauthorize"),
    }

    with _StubServer() as stub:
        result = module.check_login_start(base_url=stub.base_url)

    assert result.ok is False
    assert result.reason == "location_is_not_authorize_or_auth_login_redirect"


def test_check_login_start_rejects_authorize_redirect_when_expected_host_mismatches():
    module = _load_module()
    _StubHandler.routes = {
        "/login": (302, "https://idp.example.test/oauth2/authorize?state=abc"),
    }

    with _StubServer() as stub:
        result = module.check_login_start(
            base_url=stub.base_url,
            allowed_authorize_hosts={"auth.dev.georanking.ch"},
        )

    assert result.ok is False
    assert result.reason == "location_is_not_authorize_or_auth_login_redirect"


def test_check_login_start_accepts_authorize_redirect_when_expected_host_matches():
    module = _load_module()
    _StubHandler.routes = {
        "/login": (302, "https://auth.dev.georanking.ch/oauth2/authorize?state=abc"),
    }

    with _StubServer() as stub:
        result = module.check_login_start(
            base_url=stub.base_url,
            allowed_authorize_hosts={"auth.dev.georanking.ch", "www.dev.georanking.ch"},
        )

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


def test_check_login_start_passes_for_http_307_then_http_303_redirect_chain():
    module = _load_module()
    _StubHandler.routes = {
        "/login": (307, "/auth/login?next=%2Fgui&reason=manual_login"),
        "/auth/login": (303, "https://idp.example.test/oauth2/authorize?state=abc"),
    }

    with _StubServer() as stub:
        result = module.check_login_start(base_url=stub.base_url)

    assert result.ok is True
    assert result.reason == "ok"


def test_check_login_start_passes_for_single_canonical_login_hop_then_authorize_redirect():
    module = _load_module()
    _StubHandler.routes = {
        "/login?next=%2Fgui&reason=manual_login&start=1": (
            307,
            "/login?next=%2Fgui&reason=manual_login&start=1&canonical=1",
        ),
        "/login?next=%2Fgui&reason=manual_login&start=1&canonical=1": (
            302,
            "https://idp.example.test/oauth2/authorize?state=abc",
        ),
    }

    with _StubServer() as stub:
        result = module.check_login_start(base_url=stub.base_url)

    assert result.ok is True
    assert result.reason == "ok"
    assert "canonical=1" in result.request_url


def test_check_login_start_passes_for_two_canonical_login_hops_then_authorize_redirect():
    module = _load_module()
    _StubHandler.routes = {
        "/login?next=%2Fgui&reason=manual_login&start=1": (
            307,
            "/login?next=%2Fgui&reason=manual_login&start=1&canonical=1",
        ),
        "/login?next=%2Fgui&reason=manual_login&start=1&canonical=1": (
            307,
            "/login?next=%2Fgui&reason=manual_login&start=1&canonical=2",
        ),
        "/login?next=%2Fgui&reason=manual_login&start=1&canonical=2": (
            302,
            "https://idp.example.test/oauth2/authorize?state=abc",
        ),
    }

    with _StubServer() as stub:
        result = module.check_login_start(base_url=stub.base_url)

    assert result.ok is True
    assert result.reason == "ok"
    assert "canonical=2" in result.request_url


def test_check_login_start_fails_for_looping_same_login_redirect_chain():
    module = _load_module()
    _StubHandler.routes = {
        "/login?next=%2Fgui&reason=manual_login&start=1": (
            307,
            "/login?next=%2Fgui&reason=manual_login&start=1&canonical=1",
        ),
        "/login?next=%2Fgui&reason=manual_login&start=1&canonical=1": (
            307,
            "/login?next=%2Fgui&reason=manual_login&start=1&canonical=2",
        ),
        "/login?next=%2Fgui&reason=manual_login&start=1&canonical=2": (
            307,
            "/login?next=%2Fgui&reason=manual_login&start=1&canonical=1",
        ),
    }

    with _StubServer() as stub:
        result = module.check_login_start(base_url=stub.base_url)

    assert result.ok is False
    assert result.reason == "start_same_login_redirect_loop_detected"


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
    assert result.reason == "unexpected_start_status_200"


def test_check_login_start_fails_when_auth_login_redirect_misses_required_reason_query():
    module = _load_module()
    _StubHandler.routes = {
        "/login": (302, "/auth/login?next=%2Fgui"),
        "/auth/login": (302, "/login?next=%2Fgui&reason=manual_login"),
    }

    with _StubServer() as stub:
        result = module.check_login_start(base_url=stub.base_url)

    assert result.ok is False
    assert result.reason == "start_auth_login_redirect_reason_mismatch"


def test_check_login_entry_fails_for_auth_login_redirect_without_expected_next_query():
    module = _load_module()
    _StubHandler.routes = {
        "/login?next=%2Fgui&reason=manual_login": (
            302,
            "/auth/login?next=%2Fhistory&reason=manual_login",
        ),
    }

    with _StubServer() as stub:
        result = module.check_login_entry(base_url=stub.base_url)

    assert result.ok is False
    assert result.reason == "entry_auth_login_redirect_next_mismatch"


def test_check_login_start_fails_for_auth_login_redirect_without_expected_reason_query():
    module = _load_module()
    _StubHandler.routes = {
        "/login": (302, "/auth/login?next=%2Fgui&reason=manual_login_typo"),
    }

    with _StubServer() as stub:
        result = module.check_login_start(base_url=stub.base_url)

    assert result.ok is False
    assert result.reason == "start_auth_login_redirect_reason_mismatch"


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

    monkeypatch.setattr(
        module, "build_opener", lambda *_args, **_kwargs: _AlwaysFailingOpener()
    )

    with pytest.raises(RuntimeError, match="request_failed_after_retries"):
        module.check_login_start(
            base_url="https://www.dev.georanking.ch",
            max_attempts=2,
            retry_delay_seconds=0,
        )


def test_check_login_start_retries_transient_http_429_with_retry_after(monkeypatch):
    module = _load_module()

    class _FakeResponse:
        status = 302

        def __init__(self, location: str) -> None:
            self.headers = {"Location": location}

        def getcode(self) -> int:
            return self.status

    class _FlakyRateLimitOpener:
        def __init__(self) -> None:
            self.calls = 0

        def open(self, req, timeout):  # noqa: ARG002
            self.calls += 1
            if self.calls == 1:
                raise HTTPError(
                    req.full_url, 429, "Too Many Requests", {"Retry-After": "0"}, None
                )
            return _FakeResponse("https://idp.example.test/oauth2/authorize?state=abc")

    opener = _FlakyRateLimitOpener()
    monkeypatch.setattr(module, "build_opener", lambda *_args, **_kwargs: opener)

    result = module.check_login_start(
        base_url="https://www.dev.georanking.ch",
        max_attempts=2,
        retry_delay_seconds=0,
    )

    assert result.ok is True
    assert result.reason == "ok"
    assert opener.calls == 2


def test_check_login_start_retries_transient_http_429_with_stale_retry_after_uses_default_delay(
    monkeypatch,
):
    module = _load_module()

    class _FakeResponse:
        status = 302

        def __init__(self, location: str) -> None:
            self.headers = {"Location": location}

        def getcode(self) -> int:
            return self.status

    class _FlakyRateLimitOpener:
        def __init__(self) -> None:
            self.calls = 0

        def open(self, req, timeout):  # noqa: ARG002
            self.calls += 1
            if self.calls == 1:
                raise HTTPError(
                    req.full_url,
                    429,
                    "Too Many Requests",
                    {"Retry-After": "Sun, 06 Nov 1994 08:49:37 GMT"},
                    None,
                )
            return _FakeResponse("https://idp.example.test/oauth2/authorize?state=abc")

    sleep_calls: list[float] = []
    opener = _FlakyRateLimitOpener()
    monkeypatch.setattr(module, "build_opener", lambda *_args, **_kwargs: opener)
    monkeypatch.setattr(
        module.time, "sleep", lambda seconds: sleep_calls.append(seconds)
    )

    result = module.check_login_start(
        base_url="https://www.dev.georanking.ch",
        max_attempts=2,
        retry_delay_seconds=1.25,
    )

    assert result.ok is True
    assert result.reason == "ok"
    assert opener.calls == 2
    assert sleep_calls == [1.25]


def test_check_login_start_caps_retry_after_sleep_to_max_retry_delay(monkeypatch):
    module = _load_module()

    class _FakeResponse:
        status = 302

        def __init__(self, location: str) -> None:
            self.headers = {"Location": location}

        def getcode(self) -> int:
            return self.status

    class _FlakyRateLimitOpener:
        def __init__(self) -> None:
            self.calls = 0

        def open(self, req, timeout):  # noqa: ARG002
            self.calls += 1
            if self.calls == 1:
                raise HTTPError(
                    req.full_url,
                    429,
                    "Too Many Requests",
                    {"Retry-After": "120"},
                    None,
                )
            return _FakeResponse("https://idp.example.test/oauth2/authorize?state=abc")

    sleep_calls: list[float] = []
    opener = _FlakyRateLimitOpener()
    monkeypatch.setattr(module, "build_opener", lambda *_args, **_kwargs: opener)
    monkeypatch.setattr(
        module.time, "sleep", lambda seconds: sleep_calls.append(seconds)
    )

    result = module.check_login_start(
        base_url="https://www.dev.georanking.ch",
        max_attempts=2,
        retry_delay_seconds=1.25,
        max_retry_delay_seconds=3.0,
    )

    assert result.ok is True
    assert result.reason == "ok"
    assert opener.calls == 2
    assert sleep_calls == [3.0]


def test_main_includes_max_retry_delay_in_request_meta(capsys):
    module = _load_module()
    _StubHandler.routes = {
        "/login": {
            "status": 200,
            "body": "<html><body>keine start links</body></html>",
        },
    }

    with _StubServer() as stub:
        exit_code = module.main(
            ["--base-url", stub.base_url, "--max-retry-delay", "4.5"]
        )

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["phase"] == "entry"
    assert payload["request"]["max_retry_delay"] == 4.5


def test_classify_request_failure_detects_tls_cert_expired():
    module = _load_module()

    error = RuntimeError(
        "request_failed_after_retries(attempts=2, timeout_seconds=5.0): "
        "<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate has expired>"
    )

    reason = module._classify_request_failure(error)

    assert reason == "request_failed_tls_cert_has_expired"


def test_classify_request_failure_prefers_timeout_over_tls_keywords():
    module = _load_module()

    error = TimeoutError("TLS handshake timed out while connecting")

    reason = module._classify_request_failure(error)

    assert reason == "request_failed_timeout_timed_out"


def test_main_emits_classified_request_failure_reason(monkeypatch, capsys):
    module = _load_module()

    def _raise_request_failure(**_kwargs):
        raise RuntimeError(
            "request_failed_after_retries(attempts=2, timeout_seconds=5.0): "
            "<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate has expired>"
        )

    monkeypatch.setattr(module, "check_login_entry", _raise_request_failure)

    exit_code = module.main(["--base-url", "https://www.dev.georanking.ch"])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["phase"] == "request"
    assert payload["reason"] == "request_failed_tls_cert_has_expired"


def test_send_request_probe_does_not_retry_non_retryable_tls_errors(monkeypatch):
    module = _load_module()

    class _FakeOpener:
        def __init__(self):
            self.calls = 0

        def open(self, req, timeout):
            _ = (req, timeout)
            self.calls += 1
            raise RuntimeError(
                "<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
                "Hostname mismatch, certificate is not valid for 'dev.georanking.ch'. (_ssl.c:1029)>"
            )

    fake_opener = _FakeOpener()
    monkeypatch.setattr(module, "build_opener", lambda *_args, **_kwargs: fake_opener)

    sleep_calls: list[float] = []
    monkeypatch.setattr(
        module.time, "sleep", lambda seconds: sleep_calls.append(seconds)
    )

    with pytest.raises(RuntimeError, match="request_failed_after_retries"):
        module._send_request_probe(
            request_url="https://dev.georanking.ch/login?next=%2Fgui&reason=manual_login",
            timeout_seconds=5.0,
            max_attempts=8,
            retry_delay_seconds=5.0,
            max_retry_delay_seconds=10.0,
        )

    assert fake_opener.calls == 1
    assert sleep_calls == []


def test_send_request_probe_retries_retryable_generic_errors(monkeypatch):
    module = _load_module()

    class _FakeResponse:
        status = 302

        def __init__(self):
            self.headers = {
                "Location": "https://auth.dev.georanking.ch/oauth2/authorize?state=abc",
                "Content-Type": "text/html; charset=utf-8",
            }

        def getcode(self):
            return self.status

        def read(self, _limit: int):
            return b""

        def close(self):
            return None

    class _FakeOpener:
        def __init__(self):
            self.calls = 0

        def open(self, req, timeout):
            _ = (req, timeout)
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("temporary socket hiccup")
            return _FakeResponse()

    fake_opener = _FakeOpener()
    monkeypatch.setattr(module, "build_opener", lambda *_args, **_kwargs: fake_opener)

    sleep_calls: list[float] = []
    monkeypatch.setattr(
        module.time, "sleep", lambda seconds: sleep_calls.append(seconds)
    )

    result = module._send_request_probe(
        request_url="https://www.dev.georanking.ch/login?next=%2Fgui&reason=manual_login",
        timeout_seconds=5.0,
        max_attempts=2,
        retry_delay_seconds=1.75,
        max_retry_delay_seconds=10.0,
    )

    assert result.status_code == 302
    assert fake_opener.calls == 2
    assert sleep_calls == [1.75]
