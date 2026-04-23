"""Fingerprinting für Legacy-Consumer-Nachweise in OIDC-Migrationspfaden.

Erzeugt reproduzierbare Fingerprints aus Runtime-Ereignissen/Artefakten,
normalisiert Zeitstempel robust und unterstützt damit Readiness-Reports
sowie Drift-/Bestandsanalysen ohne Laufzeitnebenwirkungen.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

# --- Typdefinitionen ---
class NormalizedEvent(TypedDict):
    """Normalisiertes CloudTrail-Event."""
    event_time: str
    event_name: str
    event_source: str
    source_ip: str
    user_agent: str
    recipient_account: str
    username: str
    region: str

class FingerprintEntry(TypedDict):
    """Ein Eintrag im Fingerprint-Report."""
    rank: int
    event_count: int
    latest_event_time: str
    event_sources: list[str]
    event_names: list[str]
    source_ip: str
    user_agent: str
    recipient_account: str | None
    region: str | None

class FingerprintReport(TypedDict):
    """Struktur des Fingerprint-Reports."""
    summary: str
    generated_at_utc: str
    window_utc: dict[str, str]
    config: dict[str, Any]
    counts: dict[str, int]
    top_fingerprints: list[FingerprintEntry]
    latest_events: list[NormalizedEvent]
    status: str
    expected_exit_code: int

# --- Konstanten ---
UNKNOWN = "unknown"
_MIN_TS = datetime(1970, 1, 1, tzinfo=timezone.utc)

# --- Helferfunktionen ---
def _normalize_text(value: Any) -> str:
    """Normalisiert einen Wert zu einem String oder 'unknown'."""
    if value is None:
        return UNKNOWN
    text = str(value).strip()
    return text if text else UNKNOWN

def parse_timestamp(value: str | None) -> datetime | None:
    """Parsed einen Zeitstempel-String zu einem datetime-Objekt (UTC)."""
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

def normalize_timestamp(value: str | None) -> str:
    """Normalisiert einen Zeitstempel zu ISO-8601 UTC (z. B. '2026-04-23T12:00:00Z')."""
    parsed = parse_timestamp(value)
    if parsed is None:
        return UNKNOWN
    return parsed.isoformat().replace("+00:00", "Z")

def normalize_lookup_event(event: dict[str, Any]) -> NormalizedEvent:
    """Normalisiert ein CloudTrail-Event zu einem standardisierten Format."""
    raw_detail = event.get("CloudTrailEvent")
    detail: dict[str, Any] = {}
    if isinstance(raw_detail, str) and raw_detail:
        try:
            parsed = json.loads(raw_detail)
            if isinstance(parsed, dict):
                detail = parsed
        except json.JSONDecodeError:
            detail = {}

    user_identity = detail.get("userIdentity")
    if not isinstance(user_identity, dict):
        user_identity = {}

    return {
        "event_time": _normalize_text(event.get("eventTime") or detail.get("eventTime")),
        "event_name": _normalize_text(event.get("eventName") or detail.get("eventName")),
        "event_source": _normalize_text(event.get("EventSource") or detail.get("eventSource")),
        "source_ip": _normalize_text(detail.get("sourceIPAddress")),
        "user_agent": _normalize_text(detail.get("userAgent")),
        "recipient_account": _normalize_text(
            detail.get("recipientAccountId") or user_identity.get("accountId")
        ),
        "username": _normalize_text(event.get("Username") or user_identity.get("userName")),
        "region": _normalize_text(
            detail.get("awsRegion") or detail.get("region") or event.get("AwsRegion") or event.get("Region")
        ),
    }

def extract_records_from_lookup_page(page: dict[str, Any]) -> tuple[list[NormalizedEvent], str]:
    """Extrahiert normalisierte Events aus einer CloudTrail-Lookup-Seite."""
    events = page.get("Events")
    if not isinstance(events, list):
        events = []

    records: list[NormalizedEvent] = []
    for event in events:
        if isinstance(event, dict):
            records.append(normalize_lookup_event(event))

    next_token = page.get("NextToken")
    return records, str(next_token) if next_token else ""

def load_ndjson_records(path: Path) -> tuple[list[dict[str, Any]], int]:
    """Lädt NDJSON-Datei mit CloudTrail-Events."""
    records: list[dict[str, Any]] = []
    invalid_lines = 0
    if not path.exists():
        return records, invalid_lines

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                invalid_lines += 1
                continue
            if isinstance(item, dict):
                records.append(item)
            else:
                invalid_lines += 1

    return records, invalid_lines

def build_fingerprint_report(
    records: list[dict[str, Any]],
    *,
    start_time: str,
    end_time: str,
    lookback_hours: int,
    legacy_user: str,
    region: str,
    max_results: int,
    max_pages: int,
    pages_read: int,
    include_lookup_events: bool = False,
    include_region: bool = True,
    include_account: bool = True,
    top_limit: int = 10,
    recent_limit: int = 10,
) -> FingerprintReport:
    """Erstellt einen Fingerprint-Report aus CloudTrail-Events.

    Args:
        records: Liste von Roh-Events (CloudTrail-Format).
        start_time: Startzeit des Zeitfensters (ISO-8601).
        end_time: Endzeit des Zeitfensters (ISO-8601).
        lookback_hours: Rückwärtsblick in Stunden.
        legacy_user: Benutzername des Legacy-Consumers.
        region: AWS-Region.
        max_results: Maximal Anzahl Events pro Seite.
        max_pages: Maximal Anzahl Seiten.
        pages_read: Anzahl gelesener Seiten.
        include_lookup_events: Ob LookupEvents einbezogen werden sollen.
        include_region: Ob Region im Fingerprint berücksichtigt wird.
        include_account: Ob Account-ID im Fingerprint berücksichtigt wird.
        top_limit: Maximal Anzahl Fingerprints im Report.
        recent_limit: Maximal Anzahl letzte Events im Report.

    Returns:
        FingerprintReport: Strukturierter Report.
    """
    fingerprint_dimensions: list[str] = ["source_ip", "user_agent"]
    if include_region:
        fingerprint_dimensions.append("region")
    if include_account:
        fingerprint_dimensions.append("recipient_account")

    normalized_records: list[NormalizedEvent] = [
        normalize_lookup_event(rec) for rec in records
    ]

    if include_lookup_events:
        analyzed = normalized_records
    else:
        analyzed = [
            rec
            for rec in normalized_records
            if not (
                rec.get("event_source") == "cloudtrail.amazonaws.com"
                and rec.get("event_name") == "LookupEvents"
            )
        ]

    def event_sort_key(item: NormalizedEvent) -> tuple:
        """Sortierfunktion für Events (neueste zuerst)."""
        ts = parse_timestamp(item.get("event_time")) or _MIN_TS
        return (
            ts,
            item.get("event_source", UNKNOWN),
            item.get("event_name", UNKNOWN),
            item.get("source_ip", UNKNOWN),
            item.get("user_agent", UNKNOWN),
            item.get("recipient_account", UNKNOWN),
            item.get("region", UNKNOWN),
            item.get("username", UNKNOWN),
        )

    analyzed_sorted = sorted(analyzed, key=event_sort_key, reverse=True)

    # Fingerprint-Gruppen erstellen
    combo: dict[tuple[str, ...], dict[str, Any]] = defaultdict(
        lambda: {
            "count": 0,
            "latest": None,
            "event_sources": set(),
            "event_names": set(),
        }
    )

    for rec in analyzed_sorted:
        key = tuple(rec.get(field, UNKNOWN) for field in fingerprint_dimensions)
        entry = combo[key]
        entry["count"] += 1
        entry["event_sources"].add(rec.get("event_source", UNKNOWN))
        entry["event_names"].add(rec.get("event_name", UNKNOWN))

        ts = parse_timestamp(rec.get("event_time"))
        if ts is not None and (entry["latest"] is None or ts > entry["latest"]):
            entry["latest"] = ts

    ranked = sorted(combo.items(), key=lambda item: (-item[1]["count"], item[0]))[:top_limit]

    top_fingerprints: list[FingerprintEntry] = []
    for rank, (fingerprint_values, data) in enumerate(ranked, start=1):
        item: FingerprintEntry = {
            "rank": rank,
            "event_count": data["count"],
            "latest_event_time": (
                data["latest"].isoformat().replace("+00:00", "Z")
                if data["latest"] is not None
                else UNKNOWN
            ),
            "event_sources": sorted(data["event_sources"]),
            "event_names": sorted(data["event_names"]),
        }
        for idx, field in enumerate(fingerprint_dimensions):
            item[field] = fingerprint_values[idx]  # type: ignore[typeddict-item]
        top_fingerprints.append(item)

    recent_events = analyzed_sorted[:recent_limit]

    status_result = "found_events" if analyzed_sorted else "no_events"

    return {
        "summary": "Legacy CloudTrail Consumer Fingerprint Audit (read-only)",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "window_utc": {
            "start": start_time,
            "end": end_time,
            "lookback_hours": lookback_hours,
        },
        "config": {
            "legacy_user": legacy_user,
            "region": region,
            "max_results": max_results,
            "max_pages": max_pages,
            "pages_read": pages_read,
            "include_lookup_events": include_lookup_events,
            "fingerprint_dimensions": fingerprint_dimensions,
        },
        "counts": {
            "events_raw": len(normalized_records),
            "events_analyzed": len(analyzed_sorted),
            "lookup_events_filtered": len(normalized_records) - len(analyzed_sorted),
        },
        "top_fingerprints": top_fingerprints,
        "latest_events": recent_events,
        "status": status_result,
        "expected_exit_code": 10 if status_result == "found_events" else 0,
    }

def render_report_lines(report: FingerprintReport) -> list[str]:
    """Generiert lesbare Textzeilen aus einem Fingerprint-Report."""
    counts = report.get("counts", {})
    events_raw = int(counts.get("events_raw") or 0)
    events_analyzed = int(counts.get("events_analyzed") or 0)
    dimensions = list((report.get("config") or {}).get("fingerprint_dimensions") or ["source_ip", "user_agent"])
    include_lookup_events = bool((report.get("config") or {}).get("include_lookup_events"))

    if report.get("status") != "found_events":
        lines: list[str] = []
        if events_raw and not include_lookup_events:
            lines.append(f"Events im Fenster (raw): {events_raw}")
            lines.append("Events in Auswertung: 0 (nach Filter)")
        return lines

    lines = [
        f"Events im Fenster (raw): {events_raw}",
        f"Events in Auswertung: {events_analyzed}",
        "",
        f"Top Fingerprints ({' + '.join(dimensions)}):",
    ]

    for fp in report.get("top_fingerprints", []):
        lines.append(
            f"{int(fp.get('rank', 0)):>2}. count={int(fp.get('event_count', 0)):<3} "
            f"latest={fp.get('latest_event_time', UNKNOWN)}"
        )
        for field in dimensions:
            lines.append(f"    {field}={fp.get(field, UNKNOWN)}")
        lines.append(f"    event_sources={','.join(fp.get('event_sources') or [])}")
        lines.append(f"    event_names={','.join(fp.get('event_names') or [])}")

    lines.append("")
    lines.append("Letzte 10 Events:")
    for rec in report.get("latest_events", []):
        extra: list[str] = []
        if "region" in dimensions:
            extra.append(f"region={rec.get('region', UNKNOWN)}")
        if "recipient_account" in dimensions:
            extra.append(f"acct={rec.get('recipient_account', UNKNOWN)}")
        extra_suffix = f" | {' | '.join(extra)}" if extra else ""
        lines.append(
            f"- {normalize_timestamp(rec.get('event_time'))} | "
            f"{rec.get('event_source', UNKNOWN)}:{rec.get('event_name', UNKNOWN)} | "
            f"ip={rec.get('source_ip', UNKNOWN)} | ua={rec.get('user_agent', UNKNOWN)}{extra_suffix}"
        )

    return lines

def write_report(report_path: Path, report: FingerprintReport) -> None:
    """Schreibt einen Fingerprint-Report als JSON-Datei."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

if __name__ == "__main__":
    # Selbsttest
    test_event = {
        "eventTime": "2026-04-23T12:00:00Z",
        "eventName": "AssumeRole",
        "eventSource": "sts.amazonaws.com",
        "sourceIPAddress": "192.168.1.1",
        "userAgent": "aws-cli/2.0.0",
        "recipientAccountId": "123456789012",
        "userIdentity": {"accountId": "123456789012", "userName": "testuser"},
        "awsRegion": "eu-central-1",
    }
    normalized = normalize_lookup_event(test_event)
    print("Normalized Event:", normalized)

    report = build_fingerprint_report(
        records=[test_event],
        start_time="2026-04-23T00:00:00Z",
        end_time="2026-04-23T23:59:59Z",
        lookback_hours=24,
        legacy_user="testuser",
        region="eu-central-1",
        max_results=100,
        max_pages=1,
        pages_read=1,
    )
    print("Report Status:", report["status"])