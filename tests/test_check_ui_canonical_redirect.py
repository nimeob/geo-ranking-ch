from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


MODULE_PATH = Path("scripts/smoke/check_ui_canonical_redirect.py")


def _load_module():
    spec = importlib.util.spec_from_file_location("check_ui_canonical_redirect", MODULE_PATH)
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


def test_check_canonical_redirect_fails_for_relative_location_that_keeps_alias_host(monkeypatch):
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
            "--canonical-hosts",
            "www.dev.geo-ranking.ch, www.dev.georanking.ch",
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
