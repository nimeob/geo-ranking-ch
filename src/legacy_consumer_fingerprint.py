from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

UNKNOWN = "unknown"
_MIN_TS = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _normalize_text(value: Any) -> str:
    if value is None:
        return UNKNOWN
    text = str(value).strip()
    return text if text else UNKNOWN


def parse_timestamp(value: str | None) -> datetime | None:
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
    parsed = parse_timestamp(value)
    if parsed is None:
        return UNKNOWN
    return parsed.isoformat().replace("+00:00", "Z")


def normalize_lookup_event(event: dict[str, Any]) -> dict[str, str]:
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

    event_source = detail.get("eventSource") or event.get("EventSource")
    event_name = detail.get("eventName") or event.get("EventName")
    event_time = detail.get("eventTime") or event.get("EventTime")
    source_ip = detail.get("sourceIPAddress")
    user_agent = detail.get("userAgent")
    recipient_account = detail.get("recipientAccountId") or user_identity.get("accountId")
    username = event.get("Username") or user_identity.get("userName")
    region = detail.get("awsRegion") or detail.get("region") or event.get("AwsRegion") or event.get("Region")

    return {
        "event_time": _normalize_text(event_time),
        "event_name": _normalize_text(event_name),
        "event_source": _normalize_text(event_source),
        "source_ip": _normalize_text(source_ip),
        "user_agent": _normalize_text(user_agent),
        "recipient_account": _normalize_text(recipient_account),
        "username": _normalize_text(username),
        "region": _normalize_text(region),
    }


def extract_records_from_lookup_page(page: dict[str, Any]) -> tuple[list[dict[str, str]], str]:
    events = page.get("Events")
    if not isinstance(events, list):
        events = []

    records: list[dict[str, str]] = []
    for event in events:
        if isinstance(event, dict):
            records.append(normalize_lookup_event(event))

    next_token = page.get("NextToken")
    return records, str(next_token) if next_token else ""


def load_ndjson_records(path: Path) -> tuple[list[dict[str, Any]], int]:
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
    include_lookup_events: bool,
    include_region: bool,
    include_account: bool,
    top_limit: int = 10,
    recent_limit: int = 10,
) -> dict[str, Any]:
    fingerprint_dimensions = ["source_ip", "user_agent"]
    if include_region:
        fingerprint_dimensions.append("region")
    if include_account:
        fingerprint_dimensions.append("recipient_account")

    normalized_records = [
        {
            "event_time": _normalize_text(rec.get("event_time")),
            "event_name": _normalize_text(rec.get("event_name")),
            "event_source": _normalize_text(rec.get("event_source")),
            "source_ip": _normalize_text(rec.get("source_ip")),
            "user_agent": _normalize_text(rec.get("user_agent")),
            "recipient_account": _normalize_text(rec.get("recipient_account")),
            "username": _normalize_text(rec.get("username")),
            "region": _normalize_text(rec.get("region")),
        }
        for rec in records
    ]

    if include_lookup_events:
        analyzed = list(normalized_records)
    else:
        analyzed = [
            rec
            for rec in normalized_records
            if not (
                rec.get("event_source") == "cloudtrail.amazonaws.com"
                and rec.get("event_name") == "LookupEvents"
            )
        ]

    def event_sort_key(item: dict[str, str]) -> tuple[datetime, str, str, str, str, str, str, str]:
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

    top_fingerprints: list[dict[str, Any]] = []
    for rank, (fingerprint_values, data) in enumerate(ranked, start=1):
        item: dict[str, Any] = {
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
            item[field] = fingerprint_values[idx]
        top_fingerprints.append(item)

    recent_events = [
        {
            "event_time": rec.get("event_time", UNKNOWN),
            "event_source": rec.get("event_source", UNKNOWN),
            "event_name": rec.get("event_name", UNKNOWN),
            "source_ip": rec.get("source_ip", UNKNOWN),
            "user_agent": rec.get("user_agent", UNKNOWN),
            "recipient_account": rec.get("recipient_account", UNKNOWN),
            "username": rec.get("username", UNKNOWN),
            "region": rec.get("region", UNKNOWN),
        }
        for rec in analyzed_sorted[:recent_limit]
    ]

    status = "found_events" if analyzed_sorted else "no_events"

    return {
        "summary": "Legacy CloudTrail Consumer Fingerprint Audit (read-only)",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "window_utc": {
            "start": start_time,
            "end": end_time,
            "lookback_hours": int(lookback_hours),
        },
        "config": {
            "legacy_user": legacy_user,
            "region": region,
            "max_results": int(max_results),
            "max_pages": int(max_pages),
            "pages_read": int(pages_read),
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
        "status": status,
        "expected_exit_code": 10 if status == "found_events" else 0,
    }


def render_report_lines(report: dict[str, Any]) -> list[str]:
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
        lines.append(f"{int(fp.get('rank', 0)):>2}. count={int(fp.get('event_count', 0)):<3} latest={fp.get('latest_event_time', UNKNOWN)}")
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
            "- {event_time} | {event_source}:{event_name} | ip={source_ip} | ua={user_agent}{extra}".format(
                event_time=normalize_timestamp(rec.get("event_time")),
                event_source=rec.get("event_source", UNKNOWN),
                event_name=rec.get("event_name", UNKNOWN),
                source_ip=rec.get("source_ip", UNKNOWN),
                user_agent=rec.get("user_agent", UNKNOWN),
                extra=extra_suffix,
            )
        )

    return lines


def write_report(report_path: Path, report: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
