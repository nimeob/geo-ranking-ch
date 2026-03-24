from __future__ import annotations

import importlib.util
import json
import sys
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
