from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


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
    assert len(result.checks) == 6
    assert all(bool(item.get("ok")) for item in result.checks)


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
