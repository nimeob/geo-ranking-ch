from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.error import HTTPError


MODULE_PATH = Path("scripts/smoke/check_ui_canonical_redirect.py")


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "check_ui_canonical_redirect", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_check_canonical_redirect_succeeds_for_absolute_location(monkeypatch):
    module = _load_module()

    def _fake_probe(**kwargs):
        return module._HttpProbeResult(
            status_code=307,
            location="https://www.dev.georanking.ch/login?next=%2Fgui&reason=manual_login&start=1",
        )

    monkeypatch.setattr(module, "_send_request_probe", _fake_probe)

    result = module.check_canonical_redirect(
        base_url="https://www.dev.georanking.ch",
        canonical_origin="https://www.dev.georanking.ch",
        canonical_hosts="www.dev.geo-ranking.ch, www.dev.georanking.ch",
    )

    assert result.ok is True
    assert result.skipped is False
    assert result.reason == "ok"
    assert result.alias_host == "www.dev.geo-ranking.ch"


def test_check_canonical_redirect_accepts_equivalent_query_parameter_order(monkeypatch):
    module = _load_module()

    def _fake_probe(**kwargs):
        return module._HttpProbeResult(
            status_code=307,
            location="https://www.dev.georanking.ch/login?start=1&reason=manual_login&next=%2Fgui",
        )

    monkeypatch.setattr(module, "_send_request_probe", _fake_probe)

    result = module.check_canonical_redirect(
        base_url="https://www.dev.georanking.ch",
        canonical_origin="https://www.dev.georanking.ch",
        canonical_hosts="www.dev.geo-ranking.ch, www.dev.georanking.ch",
    )

    assert result.ok is True
    assert result.reason == "ok"


def test_check_canonical_redirect_normalizes_origin_style_alias_hosts(monkeypatch):
    module = _load_module()

    def _fake_probe(**kwargs):
        request_url = kwargs.get("request_url", "")
        assert request_url.startswith("https://www.dev.geo-ranking.ch/login?")
        return module._HttpProbeResult(
            status_code=307,
            location="https://www.dev.georanking.ch/login?next=%2Fgui&reason=manual_login&start=1",
        )

    monkeypatch.setattr(module, "_send_request_probe", _fake_probe)

    result = module.check_canonical_redirect(
        base_url="https://www.dev.georanking.ch",
        canonical_origin="https://www.dev.georanking.ch",
        canonical_hosts="https://www.dev.georanking.ch:443, https://www.dev.geo-ranking.ch",
    )

    assert result.ok is True
    assert result.alias_host == "www.dev.geo-ranking.ch"


def test_check_canonical_redirect_supports_alias_host_override(monkeypatch):
    module = _load_module()

    def _fake_probe(**kwargs):
        request_url = kwargs.get("request_url", "")
        assert request_url.startswith("https://www.dev.geo-ranking.ch/login?")
        return module._HttpProbeResult(
            status_code=307,
            location="https://www.dev.georanking.ch/login?next=%2Fgui&reason=manual_login&start=1",
        )

    monkeypatch.setattr(module, "_send_request_probe", _fake_probe)

    result = module.check_canonical_redirect(
        base_url="https://www.dev.georanking.ch",
        canonical_origin="https://www.dev.georanking.ch",
        canonical_hosts="",
        alias_host="www.dev.geo-ranking.ch",
    )

    assert result.ok is True
    assert result.skipped is False
    assert result.alias_host == "www.dev.geo-ranking.ch"


def test_check_canonical_redirect_falls_back_to_host_header_on_tls_verify_errors(
    monkeypatch,
):
    module = _load_module()

    calls: list[dict] = []

    def _fake_probe(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise RuntimeError(
                "request_failed_after_retries(attempts=2, timeout_seconds=5.0): "
                "<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed>"
            )
        return module._HttpProbeResult(
            status_code=307,
            location="https://www.dev.georanking.ch/login?next=%2Fgui&reason=manual_login&start=1",
        )

    monkeypatch.setattr(module, "_send_request_probe", _fake_probe)

    result = module.check_canonical_redirect(
        base_url="https://www.dev.georanking.ch",
        canonical_origin="https://www.dev.georanking.ch",
        canonical_hosts="",
        alias_host="www.dev.geo-ranking.ch",
        max_attempts=2,
    )

    assert result.ok is True
    assert len(calls) == 2
    assert calls[0]["request_url"].startswith("https://www.dev.geo-ranking.ch/login?")
    assert calls[1]["request_url"].startswith("https://www.dev.georanking.ch/login?")
    assert calls[1]["headers"] == {
        "Host": "www.dev.geo-ranking.ch",
        "X-Forwarded-Host": "www.dev.geo-ranking.ch",
    }


def test_check_canonical_redirect_does_not_fallback_for_non_tls_errors(monkeypatch):
    module = _load_module()

    calls: list[dict] = []

    def _fake_probe(**kwargs):
        calls.append(kwargs)
        raise RuntimeError("request_failed_after_retries(attempts=2): network down")

    monkeypatch.setattr(module, "_send_request_probe", _fake_probe)

    try:
        module.check_canonical_redirect(
            base_url="https://www.dev.georanking.ch",
            canonical_origin="https://www.dev.georanking.ch",
            canonical_hosts="",
            alias_host="www.dev.geo-ranking.ch",
            max_attempts=2,
        )
    except RuntimeError as exc:
        assert "network down" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")

    assert len(calls) == 1


def test_check_canonical_redirect_fails_for_relative_location_that_keeps_alias_host(
    monkeypatch,
):
    module = _load_module()

    def _fake_probe(**kwargs):
        return module._HttpProbeResult(
            status_code=307,
            location="/login?next=%2Fgui&reason=manual_login&start=1",
        )

    monkeypatch.setattr(module, "_send_request_probe", _fake_probe)

    result = module.check_canonical_redirect(
        base_url="https://www.dev.georanking.ch",
        canonical_origin="",
        canonical_hosts="www.dev.geo-ranking.ch, www.dev.georanking.ch",
    )

    assert result.ok is False
    assert result.skipped is False
    assert result.reason == "canonical_redirect_target_mismatch"


def test_check_canonical_redirect_skips_when_no_alias_hosts(monkeypatch):
    module = _load_module()

    def _unexpected_probe(**kwargs):
        raise AssertionError("probe should not run when no alias hosts are configured")

    monkeypatch.setattr(module, "_send_request_probe", _unexpected_probe)

    result = module.check_canonical_redirect(
        base_url="https://www.dev.georanking.ch",
        canonical_origin="https://www.dev.georanking.ch",
        canonical_hosts="www.dev.georanking.ch",
    )

    assert result.ok is True
    assert result.skipped is True
    assert result.reason == "skipped_no_alias_hosts"


def test_check_canonical_redirect_fails_for_non_redirect_status(monkeypatch):
    module = _load_module()

    def _fake_probe(**kwargs):
        return module._HttpProbeResult(status_code=200, location="")

    monkeypatch.setattr(module, "_send_request_probe", _fake_probe)

    result = module.check_canonical_redirect(
        base_url="https://www.dev.georanking.ch",
        canonical_origin="https://www.dev.georanking.ch",
        canonical_hosts="www.dev.geo-ranking.ch, www.dev.georanking.ch",
    )

    assert result.ok is False
    assert result.reason == "unexpected_status_200"


def test_check_canonical_redirect_fails_for_target_mismatch(monkeypatch):
    module = _load_module()

    def _fake_probe(**kwargs):
        return module._HttpProbeResult(
            status_code=307,
            location="https://www.dev.georanking.ch/login?next=%2Fjobs&reason=manual_login&start=1",
        )

    monkeypatch.setattr(module, "_send_request_probe", _fake_probe)

    result = module.check_canonical_redirect(
        base_url="https://www.dev.georanking.ch",
        canonical_origin="https://www.dev.georanking.ch",
        canonical_hosts="www.dev.geo-ranking.ch, www.dev.georanking.ch",
    )

    assert result.ok is False
    assert result.reason == "canonical_redirect_target_mismatch"


def test_main_writes_json_out_alias(tmp_path, capsys, monkeypatch):
    module = _load_module()

    def _fake_probe(**kwargs):
        return module._HttpProbeResult(
            status_code=307,
            location="https://www.dev.georanking.ch/login?next=%2Fgui&reason=manual_login&start=1",
        )

    monkeypatch.setattr(module, "_send_request_probe", _fake_probe)

    output_path = tmp_path / "canonical-smoke.json"
    exit_code = module.main(
        [
            "--base-url",
            "https://www.dev.georanking.ch",
            "--alias-host",
            "www.dev.geo-ranking.ch",
            "--json-out",
            str(output_path),
        ]
    )

    assert exit_code == 0

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is True

    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["ok"] is True
    assert written["alias_host"] == "www.dev.geo-ranking.ch"


def test_send_request_probe_honors_retry_after_header(monkeypatch):
    module = _load_module()

    class _FakeResponse:
        status = 307

        def __init__(self):
            self.headers = {
                "Location": "https://www.dev.georanking.ch/login?next=%2Fgui&reason=manual_login&start=1"
            }

        def getcode(self):
            return self.status

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
    monkeypatch.setattr(
        module.time, "sleep", lambda seconds: sleep_calls.append(seconds)
    )

    result = module._send_request_probe(
        request_url="https://www.dev.geo-ranking.ch/login?next=%2Fgui&reason=manual_login&start=1",
        timeout_seconds=5.0,
        max_attempts=2,
        retry_delay_seconds=2.0,
    )

    assert result.status_code == 307
    assert fake_opener.calls == 2
    assert sleep_calls == [7.0]


def test_send_request_probe_caps_retry_after_to_max_retry_delay(monkeypatch):
    module = _load_module()

    class _FakeResponse:
        status = 307

        def __init__(self):
            self.headers = {
                "Location": "https://www.dev.georanking.ch/login?next=%2Fgui&reason=manual_login&start=1"
            }

        def getcode(self):
            return self.status

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
    monkeypatch.setattr(
        module.time, "sleep", lambda seconds: sleep_calls.append(seconds)
    )

    result = module._send_request_probe(
        request_url="https://www.dev.geo-ranking.ch/login?next=%2Fgui&reason=manual_login&start=1",
        timeout_seconds=5.0,
        max_attempts=2,
        retry_delay_seconds=2.0,
        max_retry_delay_seconds=3.5,
    )

    assert result.status_code == 307
    assert fake_opener.calls == 2
    assert sleep_calls == [3.5]


def test_send_request_probe_falls_back_to_default_retry_delay(monkeypatch):
    module = _load_module()

    class _FakeResponse:
        status = 307

        def __init__(self):
            self.headers = {
                "Location": "https://www.dev.georanking.ch/login?next=%2Fgui&reason=manual_login&start=1"
            }

        def getcode(self):
            return self.status

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
    monkeypatch.setattr(
        module.time, "sleep", lambda seconds: sleep_calls.append(seconds)
    )

    result = module._send_request_probe(
        request_url="https://www.dev.geo-ranking.ch/login?next=%2Fgui&reason=manual_login&start=1",
        timeout_seconds=5.0,
        max_attempts=2,
        retry_delay_seconds=2.5,
    )

    assert result.status_code == 307
    assert fake_opener.calls == 2
    assert sleep_calls == [2.5]


def test_send_request_probe_caps_http_date_retry_after_to_max_retry_delay(monkeypatch):
    module = _load_module()

    class _FakeResponse:
        status = 307

        def __init__(self):
            self.headers = {
                "Location": "https://www.dev.georanking.ch/login?next=%2Fgui&reason=manual_login&start=1"
            }

        def getcode(self):
            return self.status

        def close(self):
            return None

    class _FakeOpener:
        def __init__(self):
            self.calls = 0

        def open(self, req, timeout):
            self.calls += 1
            if self.calls == 1:
                retry_at = format_datetime(
                    datetime.now(timezone.utc) + timedelta(seconds=120), usegmt=True
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
    monkeypatch.setattr(
        module.time, "sleep", lambda seconds: sleep_calls.append(seconds)
    )

    result = module._send_request_probe(
        request_url="https://www.dev.geo-ranking.ch/login?next=%2Fgui&reason=manual_login&start=1",
        timeout_seconds=5.0,
        max_attempts=2,
        retry_delay_seconds=1.0,
        max_retry_delay_seconds=4.0,
    )

    assert result.status_code == 307
    assert fake_opener.calls == 2
    assert sleep_calls == [4.0]


def test_send_request_probe_uses_default_retry_delay_for_stale_http_date(monkeypatch):
    module = _load_module()

    class _FakeResponse:
        status = 307

        def __init__(self):
            self.headers = {
                "Location": "https://www.dev.georanking.ch/login?next=%2Fgui&reason=manual_login&start=1"
            }

        def getcode(self):
            return self.status

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
    monkeypatch.setattr(
        module.time, "sleep", lambda seconds: sleep_calls.append(seconds)
    )

    result = module._send_request_probe(
        request_url="https://www.dev.geo-ranking.ch/login?next=%2Fgui&reason=manual_login&start=1",
        timeout_seconds=5.0,
        max_attempts=2,
        retry_delay_seconds=2.25,
        max_retry_delay_seconds=10.0,
    )

    assert result.status_code == 307
    assert fake_opener.calls == 2
    assert sleep_calls == [2.25]
