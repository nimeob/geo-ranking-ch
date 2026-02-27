#!/usr/bin/env python3
"""Consume webhook-relay queue events for OpenClaw automation (BL-20.y.wp2.r2.wp1)."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORTS_ROOT = REPO_ROOT / "reports" / "automation" / "event-relay"
DEFAULT_STATE_FILE = DEFAULT_REPORTS_ROOT / "state" / "delivery_ids.json"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "docs" / "automation" / "event-relay-envelope.schema.json"

ALLOWED_EVENTS = {"issues", "pull_request", "workflow_dispatch"}
ALLOWED_TARGET_TYPES = {"issue", "pull_request"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue-file", required=True, help="Path to relay queue file (NDJSON)")
    parser.add_argument("--reports-root", default=str(DEFAULT_REPORTS_ROOT))
    parser.add_argument("--state-file", default=str(DEFAULT_STATE_FILE))
    parser.add_argument("--schema-path", default=str(DEFAULT_SCHEMA_PATH))
    parser.add_argument("--mode", choices=["dry-run", "apply"], default="dry-run")
    parser.add_argument(
        "--dedup-ttl-seconds",
        type=int,
        default=24 * 60 * 60,
        help="TTL window for delivery-id deduplication",
    )
    parser.add_argument(
        "--timestamp",
        default=None,
        help="Optional UTC run timestamp as YYYYMMDDTHHMMSSZ (for deterministic runs/tests).",
    )
    parser.add_argument("--max-events", type=int, default=500)
    return parser.parse_args()


def now_utc() -> datetime:
    return datetime.now(UTC)


def format_utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_run_id(explicit_timestamp: str | None) -> str:
    if explicit_timestamp:
        datetime.strptime(explicit_timestamp, "%Y%m%dT%H%M%SZ")
        return explicit_timestamp
    return now_utc().strftime("%Y%m%dT%H%M%SZ")


def parse_iso8601(value: str) -> bool:
    candidate = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(candidate)
        return True
    except ValueError:
        return False


def _require_non_empty_str(payload: dict[str, Any], key: str) -> tuple[str | None, str | None]:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        return None, f"missing_or_invalid:{key}"
    return value.strip(), None


def validate_envelope(payload: Any, line_no: int) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(payload, dict):
        return None, "payload_not_object"

    required_str_keys = ["delivery_id", "event", "action", "repository", "target_type", "received_at"]
    normalized: dict[str, Any] = {"line_no": line_no}

    for key in required_str_keys:
        value, error = _require_non_empty_str(payload, key)
        if error:
            return None, error
        normalized[key] = value

    if normalized["event"] not in ALLOWED_EVENTS:
        return None, "unsupported_event"

    if normalized["target_type"] not in ALLOWED_TARGET_TYPES:
        return None, "unsupported_target_type"

    target_number = payload.get("target_number")
    if not isinstance(target_number, int) or target_number <= 0:
        return None, "missing_or_invalid:target_number"
    normalized["target_number"] = target_number

    labels = payload.get("labels", [])
    if not isinstance(labels, list) or not all(isinstance(item, str) for item in labels):
        return None, "missing_or_invalid:labels"
    normalized["labels"] = labels

    source = payload.get("source", "github-webhook")
    if not isinstance(source, str) or not source.strip():
        return None, "missing_or_invalid:source"
    normalized["source"] = source.strip()

    if not parse_iso8601(normalized["received_at"]):
        return None, "missing_or_invalid:received_at_iso8601"

    return normalized, None


def load_state(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("state must be a JSON object")

    state: dict[str, float] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, (int, float)):
            state[key] = float(value)
    return state


def save_state(path: Path, state: dict[str, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def prune_state(state: dict[str, float], now_ts: float, ttl_seconds: int) -> dict[str, float]:
    if ttl_seconds <= 0:
        return {}
    threshold = now_ts - ttl_seconds
    return {delivery_id: seen_at for delivery_id, seen_at in state.items() if seen_at >= threshold}


def write_report_files(report: dict[str, Any], markdown: str, reports_root: Path) -> tuple[Path, Path, Path, Path]:
    history_dir = reports_root / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    history_json = history_dir / f"{report['run_id']}.json"
    history_md = history_dir / f"{report['run_id']}.md"
    latest_json = reports_root / "latest.json"
    latest_md = reports_root / "latest.md"

    history_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    history_md.write_text(markdown, encoding="utf-8")

    shutil.copyfile(history_json, latest_json)
    shutil.copyfile(history_md, latest_md)

    return history_json, history_md, latest_json, latest_md


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Event Relay Consumer Report")
    lines.append("")
    lines.append(f"- Run ID: `{report['run_id']}`")
    lines.append(f"- Mode: `{report['mode']}`")
    lines.append(f"- Queue file: `{report['queue_file']}`")
    lines.append(f"- Started: `{report['started_at']}`")
    lines.append(f"- Finished: `{report['finished_at']}`")
    lines.append(f"- Status: **{report['status']}**")
    lines.append(f"- Exit code: `{report['exit_code']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    summary = report["summary"]
    lines.append(f"- total: `{summary['total']}`")
    lines.append(f"- accepted: `{summary['accepted']}`")
    lines.append(f"- duplicates: `{summary['duplicates']}`")
    lines.append(f"- invalid: `{summary['invalid']}`")
    lines.append(f"- pruned_state_entries: `{summary['pruned_state_entries']}`")
    lines.append("")

    lines.append("## Events")
    for event in report["events"]:
        lines.append("")
        lines.append(
            f"- line `{event['line_no']}` · delivery `{event.get('delivery_id', '<none>')}` · status `{event['status']}`"
        )
        if "reason" in event:
            lines.append(f"  - reason: `{event['reason']}`")
        if "route" in event:
            lines.append(f"  - route: `{event['route']}`")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()

    queue_file = Path(args.queue_file)
    reports_root = Path(args.reports_root)
    state_file = Path(args.state_file)
    schema_path = Path(args.schema_path)

    if not queue_file.is_file():
        print(f"queue file not found: {queue_file}", file=sys.stderr)
        return 2

    if not schema_path.is_file():
        print(f"schema file not found: {schema_path}", file=sys.stderr)
        return 2

    if args.max_events <= 0:
        print("--max-events must be > 0", file=sys.stderr)
        return 2

    run_id = resolve_run_id(args.timestamp)
    started = time.time()

    try:
        state = load_state(state_file)
    except Exception as exc:  # pragma: no cover - defensive path
        print(f"failed to read state file {state_file}: {exc}", file=sys.stderr)
        return 3

    now_ts = time.time()
    original_state_len = len(state)
    state = prune_state(state, now_ts=now_ts, ttl_seconds=args.dedup_ttl_seconds)
    pruned_state_entries = max(0, original_state_len - len(state))

    events_out: list[dict[str, Any]] = []

    accepted = 0
    duplicates = 0
    invalid = 0

    lines = queue_file.read_text(encoding="utf-8").splitlines()
    for line_no, raw_line in enumerate(lines[: args.max_events], start=1):
        raw_line = raw_line.strip()
        if not raw_line:
            continue

        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError:
            invalid += 1
            events_out.append({"line_no": line_no, "status": "invalid", "reason": "invalid_json"})
            continue

        normalized, error = validate_envelope(payload, line_no=line_no)
        if error:
            invalid += 1
            event_result = {
                "line_no": line_no,
                "status": "invalid",
                "reason": error,
                "delivery_id": payload.get("delivery_id") if isinstance(payload, dict) else None,
            }
            events_out.append(event_result)
            continue

        assert normalized is not None

        delivery_id = normalized["delivery_id"]
        route = f"{normalized['event']}.{normalized['action']}:{normalized['target_type']}#{normalized['target_number']}"

        if delivery_id in state:
            duplicates += 1
            events_out.append(
                {
                    "line_no": line_no,
                    "delivery_id": delivery_id,
                    "status": "duplicate",
                    "route": route,
                }
            )
            continue

        state[delivery_id] = now_ts
        accepted += 1
        events_out.append(
            {
                "line_no": line_no,
                "delivery_id": delivery_id,
                "status": "accepted",
                "dispatch": "deferred-for-wp2" if args.mode == "apply" else "dry-run",
                "route": route,
            }
        )

    save_state(state_file, state)

    finished = time.time()
    total = accepted + duplicates + invalid

    report = {
        "job_id": "event-relay-consumer",
        "run_id": run_id,
        "mode": args.mode,
        "queue_file": str(queue_file),
        "schema_path": str(schema_path),
        "state_file": str(state_file),
        "started_at": format_utc(started),
        "finished_at": format_utc(finished),
        "duration_seconds": finished - started,
        "status": "pass",
        "exit_code": 0,
        "summary": {
            "total": total,
            "accepted": accepted,
            "duplicates": duplicates,
            "invalid": invalid,
            "pruned_state_entries": pruned_state_entries,
        },
        "events": events_out,
    }

    markdown = render_markdown(report)
    history_json, history_md, latest_json, latest_md = write_report_files(report, markdown, reports_root=reports_root)

    print(
        json.dumps(
            {
                "status": report["status"],
                "exit_code": report["exit_code"],
                "summary": report["summary"],
                "history_json": str(history_json),
                "history_md": str(history_md),
                "latest_json": str(latest_json),
                "latest_md": str(latest_md),
                "state_file": str(state_file),
            },
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
