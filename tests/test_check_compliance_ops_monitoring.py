"""Regressionstests für scripts/check_compliance_ops_monitoring.py (Issue #531)."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Modul dynamisch laden (vermeidet sys.path-Pollution)
# ---------------------------------------------------------------------------
_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_compliance_ops_monitoring.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_compliance_ops_monitoring", _SCRIPT_PATH)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


mod = _load_module()

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------
_NOW = datetime(2026, 3, 1, 18, 0, 0, tzinfo=timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _write_jsonl(path: Path, records: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


# ---------------------------------------------------------------------------
# _load_jsonl
# ---------------------------------------------------------------------------
class TestLoadJsonl:
    def test_missing_file_returns_empty(self, tmp_path):
        result = mod._load_jsonl(tmp_path / "nonexistent.jsonl")
        assert result == []

    def test_parses_valid_jsonl(self, tmp_path):
        p = tmp_path / "test.jsonl"
        _write_jsonl(p, [{"a": 1}, {"b": 2}])
        result = mod._load_jsonl(p)
        assert len(result) == 2
        assert result[0] == {"a": 1}

    def test_skips_blank_lines(self, tmp_path):
        p = tmp_path / "test.jsonl"
        p.write_text('{"x": 1}\n\n{"y": 2}\n', encoding="utf-8")
        assert len(mod._load_jsonl(p)) == 2

    def test_skips_malformed_lines(self, tmp_path):
        p = tmp_path / "test.jsonl"
        p.write_text('{"ok": true}\nnot-json\n{"ok2": true}\n', encoding="utf-8")
        result = mod._load_jsonl(p)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# _parse_dt
# ---------------------------------------------------------------------------
class TestParseDt:
    def test_none_returns_none(self):
        assert mod._parse_dt(None) is None

    def test_z_suffix(self):
        dt = mod._parse_dt("2026-03-01T12:00:00Z")
        assert dt is not None
        assert dt.tzinfo is not None

    def test_plus_offset(self):
        dt = mod._parse_dt("2026-03-01T12:00:00+00:00")
        assert dt is not None

    def test_invalid_returns_none(self):
        assert mod._parse_dt("not-a-date") is None


# ---------------------------------------------------------------------------
# _check_deletions
# ---------------------------------------------------------------------------
class TestCheckDeletions:
    def test_no_config_returns_skip(self):
        with patch.object(mod, "DELETION_LOG_PATH", None):
            lines, fail, warn = mod._check_deletions(_NOW)
        assert not fail
        assert not warn
        assert any("Skip" in d for _, _, d in lines)

    def test_empty_file_returns_info(self, tmp_path):
        p = tmp_path / "del.jsonl"
        _write_jsonl(p, [])
        with patch.object(mod, "DELETION_LOG_PATH", p):
            lines, fail, warn = mod._check_deletions(_NOW)
        assert not fail
        assert not warn

    def test_no_overdue_ok(self, tmp_path):
        p = tmp_path / "del.jsonl"
        future = _NOW + timedelta(days=5)
        _write_jsonl(p, [
            {"record_id": "r1", "document_id": "d1", "status": "notified",
             "execute_after": _iso(future)},
        ])
        with patch.object(mod, "DELETION_LOG_PATH", p):
            lines, fail, warn = mod._check_deletions(_NOW)
        assert not fail
        assert not warn

    def test_overdue_causes_fail(self, tmp_path):
        p = tmp_path / "del.jsonl"
        past = _NOW - timedelta(hours=1)
        _write_jsonl(p, [
            {"record_id": "r1", "document_id": "d1", "status": "notified",
             "execute_after": _iso(past)},
        ])
        with patch.object(mod, "DELETION_LOG_PATH", p), \
             patch.object(mod, "WARN_OVERDUE", 1):
            lines, fail, warn = mod._check_deletions(_NOW)
        assert fail
        assert not warn

    def test_pending_not_counted_as_overdue(self, tmp_path):
        p = tmp_path / "del.jsonl"
        past = _NOW - timedelta(hours=1)
        _write_jsonl(p, [
            {"record_id": "r1", "document_id": "d1", "status": "pending",
             "execute_after": _iso(past)},
        ])
        with patch.object(mod, "DELETION_LOG_PATH", p):
            lines, fail, warn = mod._check_deletions(_NOW)
        assert not fail


# ---------------------------------------------------------------------------
# _check_holds
# ---------------------------------------------------------------------------
class TestCheckHolds:
    def test_no_config_returns_skip(self):
        with patch.object(mod, "HOLD_LOG_PATH", None):
            lines, fail, warn = mod._check_holds(_NOW)
        assert not fail
        assert not warn

    def test_no_overdue_ok(self, tmp_path):
        p = tmp_path / "holds.jsonl"
        future = _NOW + timedelta(days=10)
        _write_jsonl(p, [
            {"hold_id": "h1", "document_id": "d1", "status": "active",
             "review_due_at": _iso(future)},
        ])
        with patch.object(mod, "HOLD_LOG_PATH", p):
            lines, fail, warn = mod._check_holds(_NOW)
        assert not fail
        assert not warn

    def test_overdue_review_causes_fail(self, tmp_path):
        p = tmp_path / "holds.jsonl"
        past = _NOW - timedelta(days=1)
        _write_jsonl(p, [
            {"hold_id": "h1", "document_id": "d1", "status": "active",
             "review_due_at": _iso(past)},
        ])
        with patch.object(mod, "HOLD_LOG_PATH", p):
            lines, fail, warn = mod._check_holds(_NOW)
        assert fail
        assert not warn

    def test_released_hold_not_overdue(self, tmp_path):
        p = tmp_path / "holds.jsonl"
        past = _NOW - timedelta(days=1)
        _write_jsonl(p, [
            {"hold_id": "h1", "document_id": "d1", "status": "released",
             "review_due_at": _iso(past)},
        ])
        with patch.object(mod, "HOLD_LOG_PATH", p):
            lines, fail, warn = mod._check_holds(_NOW)
        assert not fail


# ---------------------------------------------------------------------------
# _check_export_errors
# ---------------------------------------------------------------------------
class TestCheckExportErrors:
    def test_no_file_returns_skip(self, tmp_path):
        p = tmp_path / "export.jsonl"
        with patch.object(mod, "EXPORT_LOG_PATH", p):
            lines, fail, warn = mod._check_export_errors(_NOW)
        assert not fail
        assert not warn

    def test_no_errors_ok(self, tmp_path):
        p = tmp_path / "export.jsonl"
        entries = [{"status": "ok", "exported_at_utc": _iso(_NOW - timedelta(minutes=i))}
                   for i in range(10)]
        _write_jsonl(p, entries)
        with patch.object(mod, "EXPORT_LOG_PATH", p), \
             patch.object(mod, "MONITOR_HOURS", 24), \
             patch.object(mod, "WARN_EXPORT_PCT", 10.0), \
             patch.object(mod, "FAIL_EXPORT_PCT", 25.0):
            lines, fail, warn = mod._check_export_errors(_NOW)
        assert not fail
        assert not warn

    def test_high_error_rate_fail(self, tmp_path):
        p = tmp_path / "export.jsonl"
        entries = (
            [{"status": "error", "exported_at_utc": _iso(_NOW - timedelta(minutes=i))} for i in range(30)]
            + [{"status": "ok", "exported_at_utc": _iso(_NOW - timedelta(minutes=i))} for i in range(70)]
        )
        _write_jsonl(p, entries)
        with patch.object(mod, "EXPORT_LOG_PATH", p), \
             patch.object(mod, "MONITOR_HOURS", 24), \
             patch.object(mod, "WARN_EXPORT_PCT", 10.0), \
             patch.object(mod, "FAIL_EXPORT_PCT", 25.0):
            lines, fail, warn = mod._check_export_errors(_NOW)
        assert fail
        assert not warn

    def test_medium_error_rate_warn(self, tmp_path):
        p = tmp_path / "export.jsonl"
        entries = (
            [{"status": "error", "exported_at_utc": _iso(_NOW - timedelta(minutes=i))} for i in range(15)]
            + [{"status": "ok", "exported_at_utc": _iso(_NOW - timedelta(minutes=i))} for i in range(85)]
        )
        _write_jsonl(p, entries)
        with patch.object(mod, "EXPORT_LOG_PATH", p), \
             patch.object(mod, "MONITOR_HOURS", 24), \
             patch.object(mod, "WARN_EXPORT_PCT", 10.0), \
             patch.object(mod, "FAIL_EXPORT_PCT", 25.0):
            lines, fail, warn = mod._check_export_errors(_NOW)
        assert not fail
        assert warn

    def test_entries_outside_window_excluded(self, tmp_path):
        p = tmp_path / "export.jsonl"
        # 5 Fehler innerhalb des Fensters, 20 Fehler außerhalb
        entries = (
            [{"status": "error", "exported_at_utc": _iso(_NOW - timedelta(hours=1))} for _ in range(5)]
            + [{"status": "error", "exported_at_utc": _iso(_NOW - timedelta(hours=48))} for _ in range(20)]
            + [{"status": "ok", "exported_at_utc": _iso(_NOW - timedelta(hours=1))} for _ in range(95)]
        )
        _write_jsonl(p, entries)
        with patch.object(mod, "EXPORT_LOG_PATH", p), \
             patch.object(mod, "MONITOR_HOURS", 24), \
             patch.object(mod, "WARN_EXPORT_PCT", 10.0), \
             patch.object(mod, "FAIL_EXPORT_PCT", 25.0):
            lines, fail, warn = mod._check_export_errors(_NOW)
        # 5 errors of 100 = 5% → OK
        assert not fail
        assert not warn


# ---------------------------------------------------------------------------
# main() Integration
# ---------------------------------------------------------------------------
class TestMain:
    def test_ok_exit_code(self, tmp_path, capsys):
        export_p = tmp_path / "export.jsonl"
        _write_jsonl(export_p, [
            {"status": "ok", "exported_at_utc": _iso(_NOW - timedelta(minutes=5))}
        ])
        with patch.object(mod, "DELETION_LOG_PATH", None), \
             patch.object(mod, "HOLD_LOG_PATH", None), \
             patch.object(mod, "EXPORT_LOG_PATH", export_p):
            rc = mod.main()
        assert rc == 0
        captured = capsys.readouterr()
        assert "Ergebnis: OK" in captured.out

    def test_fail_exit_code_on_overdue_deletion(self, tmp_path, capsys):
        del_p = tmp_path / "del.jsonl"
        export_p = tmp_path / "export.jsonl"
        past = _NOW - timedelta(hours=1)
        _write_jsonl(del_p, [
            {"record_id": "r1", "document_id": "d1", "status": "notified",
             "execute_after": _iso(past)},
        ])
        _write_jsonl(export_p, [
            {"status": "ok", "exported_at_utc": _iso(_NOW - timedelta(minutes=5))}
        ])
        with patch.object(mod, "DELETION_LOG_PATH", del_p), \
             patch.object(mod, "HOLD_LOG_PATH", None), \
             patch.object(mod, "EXPORT_LOG_PATH", export_p), \
             patch.object(mod, "WARN_OVERDUE", 1):
            rc = mod.main()
        assert rc == 20
        captured = capsys.readouterr()
        assert "FAIL" in captured.out


# ---------------------------------------------------------------------------
# Docs-Regression: Runbook vorhanden und vollständig
# ---------------------------------------------------------------------------
class TestRunbookDocs:
    _RUNBOOK = Path(__file__).resolve().parents[1] / "docs" / "compliance" / "COMPLIANCE_OPS_MONITORING_V1.md"

    def test_runbook_exists(self):
        assert self._RUNBOOK.exists(), f"Runbook fehlt: {self._RUNBOOK}"

    def test_runbook_has_required_sections(self):
        text = self._RUNBOOK.read_text(encoding="utf-8")
        for section in ("Löschjobs", "Hold-Bestand", "Fehlerquote", "Schwellenwert", "Exit-Code"):
            assert section in text, f"Pflichtsektion '{section}' fehlt im Runbook"

    def test_script_exists(self):
        assert _SCRIPT_PATH.exists(), f"Monitoring-Skript fehlt: {_SCRIPT_PATH}"
