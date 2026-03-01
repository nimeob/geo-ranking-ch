#!/usr/bin/env python3
"""Compliance Ops Monitoring — KPI-Check-Skript (Issue #531 / BL-342).

Prüft drei Compliance-Operationsmetriken und gibt ein strukturiertes
Status-/Warn-/Fail-Ergebnis aus:

  1. Löschjobs      — pending / overdue (notified past execute_after)
  2. Hold-Bestand   — aktive Holds, Holds mit überfälliger Review
  3. Fehlerquote    — Export-Fehlerrate (aus JSONL-Log, letzte 24h)

Konfiguration (Umgebungsvariablen, alle optional):
  COMPLIANCE_DELETION_LOG     — Pfad zu Löschrekord-JSONL-Snapshot
  COMPLIANCE_HOLD_LOG         — Pfad zu Hold-Rekord-JSONL-Snapshot
  COMPLIANCE_EXPORT_LOG_PATH  — Pfad zu Export-Log-JSONL (Standard: artifacts/compliance/export/export_log_v1.jsonl)
  COMPLIANCE_MONITOR_HOURS    — Analyse-Fenster für Fehlerquote in Stunden (Standard: 24)
  COMPLIANCE_WARN_OVERDUE     — Mindestanzahl überfälliger Items für WARN (Standard: 1)
  COMPLIANCE_FAIL_EXPORT_PCT  — Export-Fehlerrate (%) für FAIL-Schwelle (Standard: 25.0)
  COMPLIANCE_WARN_EXPORT_PCT  — Export-Fehlerrate (%) für WARN-Schwelle (Standard: 10.0)

Exit-Codes:
  0  — OK (alle Checks bestanden, keine Warnungen)
  10 — WARN (mindestens eine Warnung, kein harter Fehler)
  20 — FAIL (mindestens ein kritischer Check gescheitert)
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Repo-Wurzel ermitteln
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------
_DEFAULT_EXPORT_LOG = _REPO_ROOT / "artifacts" / "compliance" / "export" / "export_log_v1.jsonl"


def _env_path(var: str, default: Optional[Path] = None) -> Optional[Path]:
    raw = os.getenv(var, "").strip()
    if raw:
        return Path(raw)
    return default


def _env_float(var: str, default: float) -> float:
    raw = os.getenv(var, "").strip()
    try:
        return float(raw) if raw else default
    except ValueError:
        return default


def _env_int(var: str, default: int) -> int:
    raw = os.getenv(var, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


DELETION_LOG_PATH: Optional[Path] = _env_path("COMPLIANCE_DELETION_LOG")
HOLD_LOG_PATH: Optional[Path] = _env_path("COMPLIANCE_HOLD_LOG")
EXPORT_LOG_PATH: Path = _env_path("COMPLIANCE_EXPORT_LOG_PATH", _DEFAULT_EXPORT_LOG)  # type: ignore[assignment]
MONITOR_HOURS: int = _env_int("COMPLIANCE_MONITOR_HOURS", 24)
WARN_OVERDUE: int = _env_int("COMPLIANCE_WARN_OVERDUE", 1)
FAIL_EXPORT_PCT: float = _env_float("COMPLIANCE_FAIL_EXPORT_PCT", 25.0)
WARN_EXPORT_PCT: float = _env_float("COMPLIANCE_WARN_EXPORT_PCT", 10.0)

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Lädt JSONL-Datei; gibt leere Liste zurück, wenn Datei fehlt."""
    if not path.exists():
        return []
    records: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError:
                pass  # Defekte Zeilen überspringen
    return records


def _parse_dt(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    # Unterstützt ISO-Format mit/ohne Z-Suffix
    normalized = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Check-Funktionen
# ---------------------------------------------------------------------------

StatusLine = Tuple[str, str, str]  # (symbol, label, detail)


def _check_deletions(now: datetime) -> Tuple[List[StatusLine], bool, bool]:
    """Prüft Löschrekord-Snapshot: pending/notified Counts und Overdue."""
    fail = False
    warn = False
    lines: List[StatusLine] = []

    if DELETION_LOG_PATH is None:
        lines.append(("ℹ️ ", "Löschjob-Log", "Kein COMPLIANCE_DELETION_LOG konfiguriert — Skip"))
        return lines, fail, warn

    records = _load_jsonl(DELETION_LOG_PATH)
    if not records:
        lines.append(("ℹ️ ", "Löschjob-Log", f"Keine Einträge in {DELETION_LOG_PATH}"))
        return lines, fail, warn

    pending = [r for r in records if r.get("status") == "pending"]
    notified = [r for r in records if r.get("status") == "notified"]
    executed = [r for r in records if r.get("status") == "executed"]
    canceled = [r for r in records if r.get("status") == "canceled"]

    # Überfällig: notified, aber execute_after liegt in der Vergangenheit
    overdue = [
        r for r in notified
        if (dt := _parse_dt(r.get("execute_after"))) is not None and dt <= now
    ]

    lines.append(("✅", "Löschjob-Counts",
                  f"pending={len(pending)}, notified={len(notified)}, executed={len(executed)}, canceled={len(canceled)}"))

    if overdue:
        count = len(overdue)
        ids = ", ".join(r.get("record_id", "?")[:8] for r in overdue[:3])
        extra = f" (…+{count-3})" if count > 3 else ""
        if count >= WARN_OVERDUE:
            lines.append(("❌", "Löschjobs-Overdue",
                          f"{count} überfällige Löschjobs (notified, execute_after abgelaufen): {ids}{extra}"))
            fail = True
        else:
            lines.append(("⚠️ ", "Löschjobs-Overdue",
                          f"{count} überfällige Löschjobs (unterhalb WARN-Schwelle): {ids}{extra}"))
            warn = True
    else:
        lines.append(("✅", "Löschjobs-Overdue", "Keine überfälligen Löschjobs"))

    return lines, fail, warn


def _check_holds(now: datetime) -> Tuple[List[StatusLine], bool, bool]:
    """Prüft Hold-Rekord-Snapshot: aktive Holds und überfällige Reviews."""
    fail = False
    warn = False
    lines: List[StatusLine] = []

    if HOLD_LOG_PATH is None:
        lines.append(("ℹ️ ", "Hold-Bestand", "Kein COMPLIANCE_HOLD_LOG konfiguriert — Skip"))
        return lines, fail, warn

    records = _load_jsonl(HOLD_LOG_PATH)
    if not records:
        lines.append(("ℹ️ ", "Hold-Bestand", f"Keine Einträge in {HOLD_LOG_PATH}"))
        return lines, fail, warn

    active = [r for r in records if r.get("status") == "active"]
    released = [r for r in records if r.get("status") == "released"]

    # Überfällige Review: aktive Holds mit review_due_at in der Vergangenheit
    overdue_review = [
        r for r in active
        if (dt := _parse_dt(r.get("review_due_at"))) is not None and dt <= now
    ]

    lines.append(("✅", "Hold-Bestand",
                  f"aktiv={len(active)}, released={len(released)}"))

    if overdue_review:
        count = len(overdue_review)
        ids = ", ".join(r.get("hold_id", "?")[:8] for r in overdue_review[:3])
        extra = f" (…+{count-3})" if count > 3 else ""
        lines.append(("❌", "Hold-Review-Overdue",
                      f"{count} Holds mit überfälliger Review-Frist: {ids}{extra}"))
        fail = True
    else:
        lines.append(("✅", "Hold-Review-Overdue", "Keine Holds mit überfälliger Review-Frist"))

    return lines, fail, warn


def _check_export_errors(now: datetime) -> Tuple[List[StatusLine], bool, bool]:
    """Prüft Export-Fehlerquote aus JSONL-Log (letztes MONITOR_HOURS-Stunden-Fenster)."""
    fail = False
    warn = False
    lines: List[StatusLine] = []

    records = _load_jsonl(EXPORT_LOG_PATH)

    if not records:
        lines.append(("ℹ️ ", "Export-Log", f"Keine Einträge in {EXPORT_LOG_PATH} — Skip"))
        return lines, fail, warn

    # Fenster: letzte N Stunden
    cutoff = now - timedelta(hours=MONITOR_HOURS)
    window = []
    for r in records:
        ts_raw = r.get("exported_at_utc") or r.get("logged_at_utc") or r.get("timestamp")
        ts = _parse_dt(ts_raw)
        if ts is None or ts >= cutoff:
            window.append(r)

    total = len(window)
    errors = sum(1 for r in window if r.get("status") == "error")
    error_pct = (errors / total * 100.0) if total > 0 else 0.0

    lines.append(("✅", "Export-Log",
                  f"Einträge (letzte {MONITOR_HOURS}h): total={total}, errors={errors}, rate={error_pct:.1f}%"))

    if total == 0:
        lines.append(("ℹ️ ", "Export-Fehlerquote", "Kein Export-Traffic im Beobachtungsfenster"))
    elif error_pct >= FAIL_EXPORT_PCT:
        lines.append(("❌", "Export-Fehlerquote",
                      f"Fehlerquote {error_pct:.1f}% ≥ FAIL-Schwelle {FAIL_EXPORT_PCT:.1f}%"))
        fail = True
    elif error_pct >= WARN_EXPORT_PCT:
        lines.append(("⚠️ ", "Export-Fehlerquote",
                      f"Fehlerquote {error_pct:.1f}% ≥ WARN-Schwelle {WARN_EXPORT_PCT:.1f}%"))
        warn = True
    else:
        lines.append(("✅", "Export-Fehlerquote",
                      f"Fehlerquote {error_pct:.1f}% unterhalb Warn-Schwelle {WARN_EXPORT_PCT:.1f}%"))

    return lines, fail, warn


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _sym(symbol: str) -> str:
    return symbol.ljust(3)


def main() -> int:
    now = datetime.now(tz=timezone.utc)

    print("== Compliance Ops Monitoring ==")
    print(f"Zeitpunkt: {now.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(f"Fenster Fehlerquote: letzte {MONITOR_HOURS}h")
    print()

    all_lines: List[StatusLine] = []
    global_fail = False
    global_warn = False

    # --- Löschjobs ---
    print("-- Löschjobs --")
    del_lines, del_fail, del_warn = _check_deletions(now)
    for sym, label, detail in del_lines:
        print(f"  {_sym(sym)} {label}: {detail}")
    all_lines.extend(del_lines)
    global_fail = global_fail or del_fail
    global_warn = global_warn or del_warn

    print()

    # --- Hold-Bestand ---
    print("-- Hold-Bestand --")
    hold_lines, hold_fail, hold_warn = _check_holds(now)
    for sym, label, detail in hold_lines:
        print(f"  {_sym(sym)} {label}: {detail}")
    all_lines.extend(hold_lines)
    global_fail = global_fail or hold_fail
    global_warn = global_warn or hold_warn

    print()

    # --- Fehlerquote ---
    print("-- Fehlerquote (Export-Log) --")
    exp_lines, exp_fail, exp_warn = _check_export_errors(now)
    for sym, label, detail in exp_lines:
        print(f"  {_sym(sym)} {label}: {detail}")
    all_lines.extend(exp_lines)
    global_fail = global_fail or exp_fail
    global_warn = global_warn or exp_warn

    print()

    # --- Gesamtstatus ---
    if global_fail:
        print("Ergebnis: FAIL")
        return 20
    if global_warn:
        print("Ergebnis: WARN")
        return 10
    print("Ergebnis: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
