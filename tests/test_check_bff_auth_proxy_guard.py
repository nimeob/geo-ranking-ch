from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.error import HTTPError


MODULE_PATH = Path("scripts/smoke/check_bff_auth_proxy_guard.py")


def _load_module():
    spec = importlib.util.spec_from_file_location("check_bff_auth_proxy_guard", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _happy_probe(module, *, request_url: str, headers: dict[str, str], **kwargs):
    _ = kwargs
    if "/auth/login" in request_url and headers.get("X-Forwarded-Host") == "www.dev.georanking.ch":
        return module._HttpProbeResult(
            status_code=302,
            location="https://auth.dev.georanking.ch/oauth2/authorize?client_id=abc",
            body_text="",
        )

    if "/auth/" in request_url:
        return module._HttpProbeResult(
            status_code=403,
            location="",
            body_text='{"error":"external_direct_login_disabled"}',
        )

    raise AssertionError(f"unexpected probe request_url={request_url!r}")


def _happy_probe_geo_ranking_alias(module, *, request_url: str, headers: dict[str, str], **kwargs):
    _ = kwargs
    if "/auth/login" in request_url and headers.get("X-Forwarded-Host") == "www.dev.geo-ranking.ch":
        return module._HttpProbeResult(
            status_code=302,
            location="https://auth.dev.georanking.ch/oauth2/authorize?client_id=abc",
            body_text="",
        )

    if "/auth/" in request_url:
        return module._HttpProbeResult(
            status_code=403,
            location="",
            body_text='{"error":"external_direct_login_disabled"}',
        )

    raise AssertionError(f"unexpected probe request_url={request_url!r}")


def test_check_auth_proxy_guard_passes_for_trusted_and_fail_closed_paths(monkeypatch):
    module = _load_module()
    monkeypatch.setattr(module, "_send_request_probe", lambda **kwargs: _happy_probe(module, **kwargs))

    result = module.check_auth_proxy_guard(
        api_base_url="https://api.dev.georanking.ch",
        ui_base_url="https://www.dev.georanking.ch",
        trusted_forwarded_host="",
        untrusted_forwarded_host="evil.example.test",
        timeout_seconds=3,
        max_attempts=1,
        retry_delay_seconds=0,
    )

    assert result.ok is True
    assert result.reason == "ok"
    assert result.trusted_forwarded_host == "www.dev.georanking.ch"
    assert "auth.dev.georanking.ch" in result.expected_authorize_hosts
    assert "www.dev.georanking.ch" in result.expected_authorize_hosts
    assert len(result.checks) == 6
    assert all(bool(item.get("ok")) for item in result.checks)


def test_check_auth_proxy_guard_accepts_geo_ranking_alias_default_authorize_hosts(monkeypatch):
    module = _load_module()
    monkeypatch.setattr(
        module,
        "_send_request_probe",
        lambda **kwargs: _happy_probe_geo_ranking_alias(module, **kwargs),
    )

    result = module.check_auth_proxy_guard(
        api_base_url="https://api.dev.georanking.ch",
        ui_base_url="https://www.dev.geo-ranking.ch",
        trusted_forwarded_host="",
        untrusted_forwarded_host="evil.example.test",
        timeout_seconds=3,
        max_attempts=1,
        retry_delay_seconds=0,
    )

    assert result.ok is True
    assert result.reason == "ok"
    assert result.trusted_forwarded_host == "www.dev.geo-ranking.ch"
    assert "auth.dev.georanking.ch" in result.expected_authorize_hosts
    assert "auth.dev.geo-ranking.ch" in result.expected_authorize_hosts


def test_check_auth_proxy_guard_fails_when_trusted_login_no_longer_redirects(monkeypatch):
    module = _load_module()

    def _failing_probe(**kwargs):
        request_url = kwargs["request_url"]
        headers = kwargs["headers"]
        if "/auth/login" in request_url and headers.get("X-Forwarded-Host") == "www.dev.georanking.ch":
            return module._HttpProbeResult(status_code=403, location="", body_text="forbidden")
        return _happy_probe(module, **kwargs)

    monkeypatch.setattr(module, "_send_request_probe", _failing_probe)

    result = module.check_auth_proxy_guard(
        api_base_url="https://api.dev.georanking.ch",
        ui_base_url="https://www.dev.georanking.ch",
        trusted_forwarded_host="",
        untrusted_forwarded_host="evil.example.test",
        timeout_seconds=3,
        max_attempts=1,
        retry_delay_seconds=0,
    )

    assert result.ok is False
    assert result.reason == "failed_login_trusted"
    failed = [item for item in result.checks if not bool(item.get("ok"))]
    assert failed
    assert failed[0]["name"] == "login_trusted"


def test_check_auth_proxy_guard_fails_when_trusted_redirect_host_is_not_allowed(monkeypatch):
    module = _load_module()

    def _wrong_host_probe(**kwargs):
        request_url = kwargs["request_url"]
        headers = kwargs["headers"]
        if "/auth/login" in request_url and headers.get("X-Forwarded-Host") == "www.dev.georanking.ch":
            return module._HttpProbeResult(
                status_code=302,
                location="https://evil.example.test/oauth2/authorize?client_id=abc",
                body_text="",
            )
        return _happy_probe(module, **kwargs)

    monkeypatch.setattr(module, "_send_request_probe", _wrong_host_probe)

    result = module.check_auth_proxy_guard(
        api_base_url="https://api.dev.georanking.ch",
        ui_base_url="https://www.dev.georanking.ch",
        trusted_forwarded_host="",
        untrusted_forwarded_host="evil.example.test",
        timeout_seconds=3,
        max_attempts=1,
        retry_delay_seconds=0,
    )

    assert result.ok is False
    assert result.reason == "failed_login_trusted"
    failed = [item for item in result.checks if not bool(item.get("ok"))]
    assert failed
    assert failed[0]["name"] == "login_trusted"
    assert failed[0]["reason"] == "authorize_redirect_host_not_allowed"


def test_check_auth_proxy_guard_fails_when_trusted_redirect_path_lacks_authorize_segment(monkeypatch):
    module = _load_module()

    def _non_authorize_path_probe(**kwargs):
        request_url = kwargs["request_url"]
        headers = kwargs["headers"]
        if "/auth/login" in request_url and headers.get("X-Forwarded-Host") == "www.dev.georanking.ch":
            return module._HttpProbeResult(
                status_code=302,
                location="https://auth.dev.georanking.ch/login?next=%2Foauth2%2Fauthorize",
                body_text="",
            )
        return _happy_probe(module, **kwargs)

    monkeypatch.setattr(module, "_send_request_probe", _non_authorize_path_probe)

    result = module.check_auth_proxy_guard(
        api_base_url="https://api.dev.georanking.ch",
        ui_base_url="https://www.dev.georanking.ch",
        trusted_forwarded_host="",
        untrusted_forwarded_host="evil.example.test",
        timeout_seconds=3,
        max_attempts=1,
        retry_delay_seconds=0,
    )

    assert result.ok is False
    assert result.reason == "failed_login_trusted"
    failed = [item for item in result.checks if not bool(item.get("ok"))]
    assert failed
    assert failed[0]["name"] == "login_trusted"
    assert failed[0]["reason"] == "authorize_redirect_path_missing_authorize_segment"


def test_check_auth_proxy_guard_fails_when_trusted_authorize_redirect_uses_http(monkeypatch):
    module = _load_module()

    def _http_authorize_probe(**kwargs):
        request_url = kwargs["request_url"]
        headers = kwargs["headers"]
        if "/auth/login" in request_url and headers.get("X-Forwarded-Host") == "www.dev.georanking.ch":
            return module._HttpProbeResult(
                status_code=302,
                location="http://auth.dev.georanking.ch/oauth2/authorize?client_id=abc",
                body_text="",
            )
        return _happy_probe(module, **kwargs)

    monkeypatch.setattr(module, "_send_request_probe", _http_authorize_probe)

    result = module.check_auth_proxy_guard(
        api_base_url="https://api.dev.georanking.ch",
        ui_base_url="https://www.dev.georanking.ch",
        trusted_forwarded_host="",
        untrusted_forwarded_host="evil.example.test",
        timeout_seconds=3,
        max_attempts=1,
        retry_delay_seconds=0,
    )

    assert result.ok is False
    assert result.reason == "failed_login_trusted"
    failed = [item for item in result.checks if not bool(item.get("ok"))]
    assert failed
    assert failed[0]["name"] == "login_trusted"
    assert failed[0]["reason"] == "authorize_redirect_must_use_https"


def test_check_auth_proxy_guard_accepts_custom_authorize_host_override(monkeypatch):
    module = _load_module()

    def _custom_host_probe(**kwargs):
        request_url = kwargs["request_url"]
        headers = kwargs["headers"]
        if "/auth/login" in request_url and headers.get("X-Forwarded-Host") == "www.dev.georanking.ch":
            return module._HttpProbeResult(
                status_code=302,
                location="https://idp.partner.example/oidc/authorize?client_id=abc",
                body_text="",
            )
        return _happy_probe(module, **kwargs)

    monkeypatch.setattr(module, "_send_request_probe", _custom_host_probe)

    result = module.check_auth_proxy_guard(
        api_base_url="https://api.dev.georanking.ch",
        ui_base_url="https://www.dev.georanking.ch",
        trusted_forwarded_host="",
        untrusted_forwarded_host="evil.example.test",
        timeout_seconds=3,
        max_attempts=1,
        retry_delay_seconds=0,
        expected_authorize_host="idp.partner.example",
    )

    assert result.ok is True
    assert result.reason == "ok"
    assert result.expected_authorize_hosts == ["idp.partner.example"]


def test_check_auth_proxy_guard_accepts_geo_ranking_alias_authorize_host_override(monkeypatch):
    module = _load_module()
    monkeypatch.setattr(module, "_send_request_probe", lambda **kwargs: _happy_probe(module, **kwargs))

    result = module.check_auth_proxy_guard(
        api_base_url="https://api.dev.georanking.ch",
        ui_base_url="https://www.dev.georanking.ch",
        trusted_forwarded_host="",
        untrusted_forwarded_host="evil.example.test",
        timeout_seconds=3,
        max_attempts=1,
        retry_delay_seconds=0,
        expected_authorize_host="auth.dev.geo-ranking.ch",
    )

    assert result.ok is True
    assert result.reason == "ok"
    assert "auth.dev.georanking.ch" in result.expected_authorize_hosts
    assert "auth.dev.geo-ranking.ch" in result.expected_authorize_hosts


def test_check_auth_proxy_guard_adds_hint_when_api_origin_matches_ui_and_untrusted_redirects_to_login(monkeypatch):
    module = _load_module()

    def _ui_origin_probe(**kwargs):
        request_url = kwargs["request_url"]
        headers = kwargs["headers"]
        forwarded_host = headers.get("X-Forwarded-Host", "")

        if "/auth/login" in request_url and forwarded_host == "www.dev.georanking.ch":
            return module._HttpProbeResult(
                status_code=302,
                location="https://auth.dev.georanking.ch/oauth2/authorize?client_id=abc",
                body_text="",
            )

        if "/auth/" in request_url:
            return module._HttpProbeResult(
                status_code=302,
                location="/login?next=%2Fgui&reason=login_unavailable",
                body_text="",
            )

        raise AssertionError(f"unexpected probe request_url={request_url!r}")

    monkeypatch.setattr(module, "_send_request_probe", _ui_origin_probe)

    result = module.check_auth_proxy_guard(
        api_base_url="https://www.dev.georanking.ch",
        ui_base_url="https://www.dev.georanking.ch",
        trusted_forwarded_host="",
        untrusted_forwarded_host="evil.example.test",
        timeout_seconds=3,
        max_attempts=1,
        retry_delay_seconds=0,
    )

    assert result.ok is False
    assert result.reason == "failed_login_untrusted"
    assert result.hint == "api_base_url_equals_ui_base_url_use_api_origin"

    failed = [item for item in result.checks if not bool(item.get("ok"))]
    assert failed
    assert failed[0]["reason"] == "unexpected_login_unavailable_redirect"
    assert failed[0]["hint"] == "api_base_url_likely_points_to_ui_origin"


def test_main_writes_json_out_alias(tmp_path, monkeypatch, capsys):
    module = _load_module()
    monkeypatch.setattr(module, "_send_request_probe", lambda **kwargs: _happy_probe(module, **kwargs))

    output_path = tmp_path / "auth-proxy-guard.json"
    exit_code = module.main(
        [
            "--api-base-url",
            "https://api.dev.georanking.ch",
            "--ui-base-url",
            "https://www.dev.georanking.ch",
            "--json-out",
            str(output_path),
            "--max-attempts",
            "1",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is True

    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["ok"] is True
    assert written["trusted_forwarded_host"] == "www.dev.georanking.ch"
    assert "auth.dev.georanking.ch" in written["expected_authorize_hosts"]


def test_main_writes_summary_json_alias(tmp_path, monkeypatch, capsys):
    module = _load_module()
    monkeypatch.setattr(module, "_send_request_probe", lambda **kwargs: _happy_probe(module, **kwargs))

    output_path = tmp_path / "auth-proxy-guard-summary.json"
    exit_code = module.main(
        [
            "--api-base-url",
            "https://api.dev.georanking.ch",
            "--ui-base-url",
            "https://www.dev.georanking.ch",
            "--summary-json",
            str(output_path),
            "--max-attempts",
            "1",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is True

    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["ok"] is True
    assert written["trusted_forwarded_host"] == "www.dev.georanking.ch"


def test_main_accepts_json_flag_without_value(monkeypatch, capsys):
    module = _load_module()
    monkeypatch.setattr(module, "_send_request_probe", lambda **kwargs: _happy_probe(module, **kwargs))

    exit_code = module.main(
        [
            "--api-base-url",
            "https://api.dev.georanking.ch",
            "--ui-base-url",
            "https://www.dev.georanking.ch",
            "--max-attempts",
            "1",
            "--json",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is True


def test_derive_default_api_origin_from_ui_base_url():
    module = _load_module()

    assert module._derive_default_api_origin("https://www.dev.georanking.ch") == "https://api.dev.georanking.ch"
    assert module._derive_default_api_origin("https://www.dev.geo-ranking.ch") == "https://api.dev.georanking.ch"
    assert module._derive_default_api_origin("https://dev.geo-ranking.ch") == "https://api.dev.georanking.ch"
    assert module._derive_default_api_origin("https://dev.georanking.ch.") == "https://api.dev.georanking.ch"
    assert module._derive_default_api_origin("https://api.dev.georanking.ch") == "https://api.dev.georanking.ch"


def test_normalize_origin_canonicalizes_legacy_dev_non_www_ui_host():
    module = _load_module()

    assert module._normalize_origin("https://dev.geo-ranking.ch") == "https://www.dev.geo-ranking.ch"
    assert module._normalize_origin("https://dev.georanking.ch.") == "https://www.dev.georanking.ch"


def test_main_derives_api_base_url_when_only_ui_base_url_is_provided(monkeypatch, capsys):
    module = _load_module()
    monkeypatch.setattr(module, "_send_request_probe", lambda **kwargs: _happy_probe(module, **kwargs))

    exit_code = module.main(["--ui-base-url", "https://www.dev.georanking.ch", "--max-attempts", "1"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is True
    assert payload["api_base_url"] == "https://api.dev.georanking.ch"


def test_main_derives_canonical_api_host_for_geo_ranking_ui_alias(monkeypatch, capsys):
    module = _load_module()
    monkeypatch.setattr(
        module,
        "_send_request_probe",
        lambda **kwargs: _happy_probe_geo_ranking_alias(module, **kwargs),
    )

    exit_code = module.main(["--ui-base-url", "https://www.dev.geo-ranking.ch", "--max-attempts", "1"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is True
    assert payload["api_base_url"] == "https://api.dev.georanking.ch"
    assert payload["trusted_forwarded_host"] == "www.dev.geo-ranking.ch"


def test_main_canonicalizes_legacy_dev_non_www_ui_base_url(monkeypatch, capsys):
    module = _load_module()
    monkeypatch.setattr(
        module,
        "_send_request_probe",
        lambda **kwargs: _happy_probe_geo_ranking_alias(module, **kwargs),
    )

    exit_code = module.main(["--ui-base-url", "https://dev.geo-ranking.ch", "--max-attempts", "1"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is True
    assert payload["api_base_url"] == "https://api.dev.georanking.ch"
    assert payload["ui_base_url"] == "https://www.dev.geo-ranking.ch"
    assert payload["trusted_forwarded_host"] == "www.dev.geo-ranking.ch"


def test_main_returns_invalid_arguments_when_api_and_ui_base_url_are_missing(capsys):
    module = _load_module()

    exit_code = module.main(["--ui-base-url", ""])

    assert exit_code == 2
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is False
    assert payload["reason"] == "invalid_arguments:api_base_url_or_ui_base_url_required"


def test_main_returns_invalid_argument_exit_code_when_hosts_collapse(monkeypatch, capsys):
    module = _load_module()
    monkeypatch.setattr(module, "_send_request_probe", lambda **kwargs: _happy_probe(module, **kwargs))

    exit_code = module.main(
        [
            "--api-base-url",
            "https://api.dev.georanking.ch",
            "--trusted-forwarded-host",
            "www.dev.georanking.ch",
            "--untrusted-forwarded-host",
            "www.dev.georanking.ch",
        ]
    )

    assert exit_code == 2
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is False
    assert payload["reason"].startswith("invalid_arguments:")


def test_main_classifies_timeout_probe_exceptions(monkeypatch, capsys):
    module = _load_module()

    def _boom(**kwargs):
        _ = kwargs
        raise TimeoutError("timed out while connecting")

    monkeypatch.setattr(module, "check_auth_proxy_guard", _boom)

    exit_code = module.main(["--api-base-url", "https://api.dev.georanking.ch"])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is False
    assert payload["reason"] == "request_failed_timeout_timed_out"
    assert "timed out" in payload["error"]


def test_main_classifies_dns_probe_exceptions(monkeypatch, capsys):
    module = _load_module()

    def _boom(**kwargs):
        _ = kwargs
        raise RuntimeError(
            "request_failed_after_retries(attempts=5, timeout_seconds=15.0): "
            "<urlopen error [Errno -2] Name or service not known>"
        )

    monkeypatch.setattr(module, "check_auth_proxy_guard", _boom)

    exit_code = module.main(["--api-base-url", "https://api.dev.georanking.ch"])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is False
    assert payload["reason"] == "request_failed_dns_resolution"


def test_send_request_probe_honors_retry_after_header(monkeypatch):
    module = _load_module()

    class _FakeResponse:
        status = 302

        def __init__(self):
            self.headers = {"Location": "https://auth.dev.georanking.ch/oauth2/authorize"}

        def getcode(self):
            return self.status

        def read(self, _max_bytes):
            return b""

        def close(self):
            return None

    class _FakeOpener:
        def __init__(self):
            self.calls = 0

        def open(self, req, timeout):
            self.calls += 1
            if self.calls == 1:
                raise HTTPError(
                    req.full_url,
                    429,
                    "Too Many Requests",
                    hdrs={"Retry-After": "7"},
                    fp=None,
                )
            return _FakeResponse()

    fake_opener = _FakeOpener()
    monkeypatch.setattr(module, "build_opener", lambda *_args, **_kwargs: fake_opener)

    sleep_calls: list[float] = []
    monkeypatch.setattr(module.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    result = module._send_request_probe(
        request_url="https://api.dev.georanking.ch/auth/login?next=%2Fgui",
        headers={"X-Geo-Auth-Proxy": "1"},
        timeout_seconds=5.0,
        max_attempts=2,
        retry_delay_seconds=2.0,
    )

    assert result.status_code == 302
    assert fake_opener.calls == 2
    assert sleep_calls == [7.0]


def test_send_request_probe_caps_retry_after_to_max_retry_delay(monkeypatch):
    module = _load_module()

    class _FakeResponse:
        status = 302

        def __init__(self):
            self.headers = {"Location": "https://auth.dev.georanking.ch/oauth2/authorize"}

        def getcode(self):
            return self.status

        def read(self, _max_bytes):
            return b""

        def close(self):
            return None

    class _FakeOpener:
        def __init__(self):
            self.calls = 0

        def open(self, req, timeout):
            self.calls += 1
            if self.calls == 1:
                raise HTTPError(
                    req.full_url,
                    429,
                    "Too Many Requests",
                    hdrs={"Retry-After": "120"},
                    fp=None,
                )
            return _FakeResponse()

    fake_opener = _FakeOpener()
    monkeypatch.setattr(module, "build_opener", lambda *_args, **_kwargs: fake_opener)

    sleep_calls: list[float] = []
    monkeypatch.setattr(module.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    result = module._send_request_probe(
        request_url="https://api.dev.georanking.ch/auth/login?next=%2Fgui",
        headers={"X-Geo-Auth-Proxy": "1"},
        timeout_seconds=5.0,
        max_attempts=2,
        retry_delay_seconds=2.0,
        max_retry_delay_seconds=3.5,
    )

    assert result.status_code == 302
    assert fake_opener.calls == 2
    assert sleep_calls == [3.5]


def test_send_request_probe_falls_back_to_default_retry_delay(monkeypatch):
    module = _load_module()

    class _FakeResponse:
        status = 403

        def __init__(self):
            self.headers = {"Location": ""}

        def getcode(self):
            return self.status

        def read(self, _max_bytes):
            return b'{"error":"external_direct_login_disabled"}'

        def close(self):
            return None

    class _FakeOpener:
        def __init__(self):
            self.calls = 0

        def open(self, req, timeout):
            self.calls += 1
            if self.calls == 1:
                raise HTTPError(
                    req.full_url,
                    503,
                    "Service Unavailable",
                    hdrs={"Retry-After": "not-a-number"},
                    fp=None,
                )
            return _FakeResponse()

    fake_opener = _FakeOpener()
    monkeypatch.setattr(module, "build_opener", lambda *_args, **_kwargs: fake_opener)

    sleep_calls: list[float] = []
    monkeypatch.setattr(module.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    result = module._send_request_probe(
        request_url="https://api.dev.georanking.ch/auth/login?next=%2Fgui",
        headers={"X-Geo-Auth-Proxy": "1"},
        timeout_seconds=5.0,
        max_attempts=2,
        retry_delay_seconds=2.5,
    )

    assert result.status_code == 403
    assert fake_opener.calls == 2
    assert sleep_calls == [2.5]


def test_send_request_probe_caps_http_date_retry_after_to_max_retry_delay(monkeypatch):
    module = _load_module()

    class _FakeResponse:
        status = 302

        def __init__(self):
            self.headers = {"Location": "https://auth.dev.georanking.ch/oauth2/authorize?client_id=abc"}

        def getcode(self):
            return self.status

        def read(self, _max_bytes):
            return b""

        def close(self):
            return None

    class _FakeOpener:
        def __init__(self):
            self.calls = 0

        def open(self, req, timeout):
            self.calls += 1
            if self.calls == 1:
                retry_at = format_datetime(
                    datetime.now(timezone.utc) + timedelta(seconds=90), usegmt=True
                )
                raise HTTPError(
                    req.full_url,
                    429,
                    "Too Many Requests",
                    hdrs={"Retry-After": retry_at},
                    fp=None,
                )
            return _FakeResponse()

    fake_opener = _FakeOpener()
    monkeypatch.setattr(module, "build_opener", lambda *_args, **_kwargs: fake_opener)

    sleep_calls: list[float] = []
    monkeypatch.setattr(module.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    result = module._send_request_probe(
        request_url="https://api.dev.georanking.ch/auth/login?next=%2Fgui",
        headers={"X-Geo-Auth-Proxy": "1"},
        timeout_seconds=5.0,
        max_attempts=2,
        retry_delay_seconds=1.0,
        max_retry_delay_seconds=3.0,
    )

    assert result.status_code == 302
    assert fake_opener.calls == 2
    assert sleep_calls == [3.0]


def test_send_request_probe_uses_default_retry_delay_for_stale_http_date(monkeypatch):
    module = _load_module()

    class _FakeResponse:
        status = 403

        def __init__(self):
            self.headers = {"Location": ""}

        def getcode(self):
            return self.status

        def read(self, _max_bytes):
            return b'{"error":"external_direct_login_disabled"}'

        def close(self):
            return None

    class _FakeOpener:
        def __init__(self):
            self.calls = 0

        def open(self, req, timeout):
            self.calls += 1
            if self.calls == 1:
                raise HTTPError(
                    req.full_url,
                    503,
                    "Service Unavailable",
                    hdrs={"Retry-After": "Sun, 06 Nov 1994 08:49:37 GMT"},
                    fp=None,
                )
            return _FakeResponse()

    fake_opener = _FakeOpener()
    monkeypatch.setattr(module, "build_opener", lambda *_args, **_kwargs: fake_opener)

    sleep_calls: list[float] = []
    monkeypatch.setattr(module.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    result = module._send_request_probe(
        request_url="https://api.dev.georanking.ch/auth/login?next=%2Fgui",
        headers={"X-Geo-Auth-Proxy": "1"},
        timeout_seconds=5.0,
        max_attempts=2,
        retry_delay_seconds=2.75,
        max_retry_delay_seconds=10.0,
    )

    assert result.status_code == 403
    assert fake_opener.calls == 2
    assert sleep_calls == [2.75]
