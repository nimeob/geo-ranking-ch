#!/usr/bin/env python3
"""Validate GitHub webhook payloads and enqueue reduced relay envelopes.

BL-20.y.wp2.r2 remaining scope:
- Relay receiver with signature verification, repo/event allowlist, and delivery-id dedup.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_FILE = REPO_ROOT / "reports" / "automation" / "event-relay" / "receiver-state" / "delivery_ids.json"
DEFAULT_ALLOWED_EVENTS = "issues,pull_request,workflow_dispatch"
DEFAULT_ALLOWED_REPOSITORIES_ENV = "EVENT_RELAY_ALLOWED_REPOSITORIES"
DEFAULT_SECRET_ENV = "GITHUB_WEBHOOK_SECRET"
DEFAULT_PREVIOUS_SECRET_ENV = "GITHUB_WEBHOOK_SECRET_PREVIOUS"
HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headers-file", required=True, help="Path to request headers JSON object")
    parser.add_argument("--payload-file", required=True, help="Path to raw webhook payload JSON")
    parser.add_argument("--queue-file", required=True, help="Target NDJSON queue file")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE_FILE), help="Dedup state JSON path")
    parser.add_argument(
        "--dedup-ttl-seconds",
        type=int,
        default=24 * 60 * 60,
        help="TTL window for delivery-id deduplication",
    )
    parser.add_argument(
        "--allowed-events",
        default=DEFAULT_ALLOWED_EVENTS,
        help="Comma-separated allowed GitHub event names",
    )
    parser.add_argument(
        "--allowed-repositories",
        default="",
        help=(
            "Comma-separated allowlist of repositories (`owner/repo` or `owner/*`). "
            f"Falls leer, wird `{DEFAULT_ALLOWED_REPOSITORIES_ENV}` verwendet."
        ),
    )
    parser.add_argument(
        "--secret-env",
        default=DEFAULT_SECRET_ENV,
        help=f"Environment variable for current webhook secret (default: {DEFAULT_SECRET_ENV})",
    )
    parser.add_argument(
        "--previous-secret-env",
        default=DEFAULT_PREVIOUS_SECRET_ENV,
        help=(
            "Optional environment variable for previous webhook secret during rotation "
            f"(default: {DEFAULT_PREVIOUS_SECRET_ENV})"
        ),
    )
    parser.add_argument(
        "--source",
        default="github-webhook",
        help="Envelope source field value (default: github-webhook)",
    )
    return parser.parse_args()


def now_iso_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json_object(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return raw


def load_state(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    raw = load_json_object(path)
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
    return {delivery_id: ts for delivery_id, ts in state.items() if ts >= threshold}


def normalize_headers(headers: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in headers.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, (str, int, float)):
            normalized[key.strip().lower()] = str(value).strip()
    return normalized


def parse_csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def normalize_label_names(raw_labels: Any) -> list[str]:
    labels: list[str] = []
    if not isinstance(raw_labels, list):
        return labels

    for entry in raw_labels:
        if isinstance(entry, str):
            candidate = entry.strip()
        elif isinstance(entry, dict) and isinstance(entry.get("name"), str):
            candidate = entry["name"].strip()
        else:
            continue

        if candidate and candidate not in labels:
            labels.append(candidate)

    return labels


def is_repository_allowed(repository: str, allowlist: list[str]) -> bool:
    for entry in allowlist:
        if entry.endswith("/*"):
            owner = entry[:-2]
            if repository.startswith(f"{owner}/"):
                return True
            continue
        if repository == entry:
            return True
    return False


def verify_signature(payload: bytes, signature_header: str, secrets: list[str]) -> bool:
    if not signature_header.startswith("sha256="):
        return False

    provided = signature_header.split("=", 1)[1].strip().lower()
    if not HEX64_PATTERN.fullmatch(provided):
        return False

    for secret in secrets:
        digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        if hmac.compare_digest(digest, provided):
            return True
    return False


def extract_target(event: str, payload: dict[str, Any]) -> tuple[str | None, int | None, list[str], str | None]:
    if event == "issues":
        issue = payload.get("issue")
        if not isinstance(issue, dict):
            return None, None, [], "missing_or_invalid:issue"
        number = issue.get("number")
        if not isinstance(number, int) or number <= 0:
            return None, None, [], "missing_or_invalid:issue.number"
        labels = normalize_label_names(issue.get("labels", []))
        return "issue", number, labels, None

    if event == "pull_request":
        pr = payload.get("pull_request")
        if not isinstance(pr, dict):
            return None, None, [], "missing_or_invalid:pull_request"
        number = pr.get("number")
        if not isinstance(number, int) or number <= 0:
            number = payload.get("number")
        if not isinstance(number, int) or number <= 0:
            return None, None, [], "missing_or_invalid:pull_request.number"
        labels = normalize_label_names(pr.get("labels", []))
        return "pull_request", number, labels, None

    if event == "workflow_dispatch":
        client_payload = payload.get("client_payload")
        if isinstance(client_payload, dict):
            target_type = client_payload.get("target_type")
            target_number = client_payload.get("target_number")
            labels = normalize_label_names(client_payload.get("labels", []))
            if target_type in {"issue", "pull_request"} and isinstance(target_number, int) and target_number > 0:
                return target_type, target_number, labels, None

        workflow_run = payload.get("workflow_run")
        if isinstance(workflow_run, dict):
            prs = workflow_run.get("pull_requests")
            if isinstance(prs, list) and prs:
                first = prs[0]
                if isinstance(first, dict) and isinstance(first.get("number"), int) and first["number"] > 0:
                    return "pull_request", int(first["number"]), [], None

        return None, None, [], "missing_target_for:workflow_dispatch"

    return None, None, [], "unsupported_event"


def make_response(status: str, **kwargs: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"status": status}
    payload.update(kwargs)
    return payload


def main() -> int:
    args = parse_args()

    headers_path = Path(args.headers_file)
    payload_path = Path(args.payload_file)
    queue_file = Path(args.queue_file)
    state_file = Path(args.state_file)

    if not headers_path.is_file():
        print(f"headers file not found: {headers_path}", file=sys.stderr)
        return 2
    if not payload_path.is_file():
        print(f"payload file not found: {payload_path}", file=sys.stderr)
        return 2
    if args.dedup_ttl_seconds <= 0:
        print("--dedup-ttl-seconds must be > 0", file=sys.stderr)
        return 2

    try:
        headers_raw = load_json_object(headers_path)
        headers = normalize_headers(headers_raw)
    except Exception as exc:
        print(f"failed to parse headers file {headers_path}: {exc}", file=sys.stderr)
        return 2

    payload_bytes = payload_path.read_bytes()
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        print(json.dumps(make_response("rejected", reason=f"invalid_json_payload:{exc}"), ensure_ascii=False))
        return 4

    if not isinstance(payload, dict):
        print(json.dumps(make_response("rejected", reason="payload_not_object"), ensure_ascii=False))
        return 4

    event = headers.get("x-github-event", "").strip()
    if not event:
        print(json.dumps(make_response("rejected", reason="missing_header:x-github-event"), ensure_ascii=False))
        return 4

    allowed_events = set(parse_csv_list(args.allowed_events))
    if event not in allowed_events:
        print(json.dumps(make_response("rejected", reason="event_not_allowlisted", event=event), ensure_ascii=False))
        return 4

    delivery_id = headers.get("x-github-delivery", "").strip()
    if not delivery_id:
        print(json.dumps(make_response("rejected", reason="missing_header:x-github-delivery"), ensure_ascii=False))
        return 4

    signature_header = headers.get("x-hub-signature-256", "").strip()
    if not signature_header:
        print(json.dumps(make_response("rejected", reason="missing_header:x-hub-signature-256"), ensure_ascii=False))
        return 4

    active_secret = os.getenv(args.secret_env, "").strip()
    previous_secret = os.getenv(args.previous_secret_env, "").strip()
    secrets = [secret for secret in [active_secret, previous_secret] if secret]

    if not secrets:
        print(
            json.dumps(
                make_response(
                    "blocked",
                    reason="missing_webhook_secret",
                    secret_env=args.secret_env,
                    previous_secret_env=args.previous_secret_env,
                ),
                ensure_ascii=False,
            )
        )
        return 3

    if not verify_signature(payload_bytes, signature_header, secrets):
        print(
            json.dumps(
                make_response("rejected", reason="invalid_signature", delivery_id=delivery_id, event=event),
                ensure_ascii=False,
            )
        )
        return 4

    repository_data = payload.get("repository")
    repository = repository_data.get("full_name") if isinstance(repository_data, dict) else None
    if not isinstance(repository, str) or not repository.strip() or "/" not in repository:
        print(json.dumps(make_response("rejected", reason="missing_or_invalid:repository.full_name"), ensure_ascii=False))
        return 4

    repositories_arg = args.allowed_repositories.strip()
    repositories_raw = repositories_arg or os.getenv(DEFAULT_ALLOWED_REPOSITORIES_ENV, "")
    allowlist = parse_csv_list(repositories_raw)
    if not allowlist:
        print(
            json.dumps(
                make_response(
                    "blocked",
                    reason="missing_repository_allowlist",
                    allowlist_source=f"--allowed-repositories or {DEFAULT_ALLOWED_REPOSITORIES_ENV}",
                ),
                ensure_ascii=False,
            )
        )
        return 3

    if not is_repository_allowed(repository.strip(), allowlist):
        print(
            json.dumps(
                make_response("rejected", reason="repository_not_allowlisted", repository=repository, event=event),
                ensure_ascii=False,
            )
        )
        return 4

    action = payload.get("action")
    if not isinstance(action, str) or not action.strip():
        print(json.dumps(make_response("rejected", reason="missing_or_invalid:action", event=event), ensure_ascii=False))
        return 4

    target_type, target_number, labels, target_error = extract_target(event, payload)
    if target_error:
        print(json.dumps(make_response("rejected", reason=target_error, event=event), ensure_ascii=False))
        return 4

    now_ts = time.time()
    try:
        state = load_state(state_file)
    except Exception as exc:
        print(
            json.dumps(
                make_response("blocked", reason=f"invalid_state_file:{exc}", state_file=str(state_file)),
                ensure_ascii=False,
            )
        )
        return 3

    state = prune_state(state, now_ts=now_ts, ttl_seconds=args.dedup_ttl_seconds)

    if delivery_id in state:
        save_state(state_file, state)
        print(
            json.dumps(
                make_response(
                    "duplicate",
                    delivery_id=delivery_id,
                    event=event,
                    repository=repository,
                    queue_file=str(queue_file),
                    state_file=str(state_file),
                ),
                ensure_ascii=False,
            )
        )
        return 0

    envelope = {
        "delivery_id": delivery_id,
        "event": event,
        "action": action.strip(),
        "repository": repository.strip(),
        "target_type": target_type,
        "target_number": int(target_number),
        "labels": labels,
        "received_at": now_iso_utc(),
        "source": args.source.strip() or "github-webhook",
    }

    queue_file.parent.mkdir(parents=True, exist_ok=True)
    with queue_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(envelope, ensure_ascii=False) + "\n")

    state[delivery_id] = now_ts
    save_state(state_file, state)

    print(
        json.dumps(
            make_response(
                "accepted",
                delivery_id=delivery_id,
                event=event,
                repository=repository,
                queue_file=str(queue_file),
                state_file=str(state_file),
                envelope=envelope,
            ),
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
