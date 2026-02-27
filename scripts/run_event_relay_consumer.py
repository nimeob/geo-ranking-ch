#!/usr/bin/env python3
"""Consume webhook-relay queue events for OpenClaw automation.

BL-20.y.wp2.r2:
- Queue-Consumer-Fundament (WP1)
- issues.* -> Worker-Claim-Reconcile dispatch (WP2)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error, parse, request

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORTS_ROOT = REPO_ROOT / "reports" / "automation" / "event-relay"
DEFAULT_STATE_FILE = DEFAULT_REPORTS_ROOT / "state" / "delivery_ids.json"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "docs" / "automation" / "event-relay-envelope.schema.json"

ALLOWED_EVENTS = {"issues", "pull_request", "workflow_dispatch"}
ALLOWED_TARGET_TYPES = {"issue", "pull_request"}
RECONCILE_TRIGGER_ACTIONS = {"opened", "reopened", "closed", "labeled", "unlabeled", "edited"}

PRIORITY_RANK = {
    "priority:P0": 0,
    "priority:P1": 1,
    "priority:P2": 2,
    "priority:P3": 3,
}

DEMOTION_COMMENT_TEMPLATE = (
    "⏸️ Claim-Priorität aktiv: Es gibt aktuell höher priorisierte TODO-Issues "
    "({active_priority}). Dieses Issue wurde daher temporär auf `status:blocked` gesetzt."
)


@dataclass
class ReconcileMutation:
    issue_number: int
    action: str
    before_labels: list[str]
    after_labels: list[str]
    comment: str | None = None


class GitHubApiError(RuntimeError):
    """Raised when GitHub API calls fail."""


class GitHubClient:
    def __init__(self, token: str, base_url: str = "https://api.github.com") -> None:
        if not token.strip():
            raise ValueError("GitHub token must not be empty")
        self._token = token.strip()
        self._base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        url = f"{self._base_url}/{path.lstrip('/')}"
        data = None
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "geo-ranking-ch-event-relay-consumer",
        }
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = request.Request(url=url, method=method, data=data, headers=headers)
        try:
            with request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
        except error.HTTPError as exc:  # pragma: no cover - network path
            detail = exc.read().decode("utf-8", errors="replace")
            raise GitHubApiError(f"{method} {url} failed: HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:  # pragma: no cover - network path
            raise GitHubApiError(f"{method} {url} failed: {exc}") from exc

        if not body:
            return None
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise GitHubApiError(f"{method} {url} returned invalid JSON") from exc

    def list_open_issues(self, repository: str) -> list[dict[str, Any]]:
        owner, repo = parse_repository(repository)
        page = 1
        all_issues: list[dict[str, Any]] = []

        while True:
            query = parse.urlencode({"state": "open", "per_page": 100, "page": page})
            payload = self._request("GET", f"repos/{owner}/{repo}/issues?{query}")
            if not isinstance(payload, list):
                raise GitHubApiError("unexpected response shape for list_open_issues")
            if not payload:
                break
            all_issues.extend(payload)
            if len(payload) < 100:
                break
            page += 1

        return all_issues

    def set_issue_labels(self, repository: str, issue_number: int, labels: list[str]) -> None:
        owner, repo = parse_repository(repository)
        self._request(
            "PATCH",
            f"repos/{owner}/{repo}/issues/{issue_number}",
            payload={"labels": labels},
        )

    def create_issue_comment(self, repository: str, issue_number: int, body: str) -> None:
        owner, repo = parse_repository(repository)
        self._request(
            "POST",
            f"repos/{owner}/{repo}/issues/{issue_number}/comments",
            payload={"body": body},
        )


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
    parser.add_argument(
        "--issues-snapshot",
        default=None,
        help=(
            "Optional local JSON file with open issues snapshot. "
            "When set, reconcile dispatch runs against this file instead of GitHub API "
            "(useful for integration tests/shadow runs)."
        ),
    )
    parser.add_argument(
        "--github-token-env",
        default="GH_TOKEN",
        help="Environment variable containing GitHub token for live reconcile mutations (default: GH_TOKEN).",
    )
    parser.add_argument(
        "--github-base-url",
        default="https://api.github.com",
        help="GitHub API base URL (default: https://api.github.com).",
    )
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


def parse_repository(repository: str) -> tuple[str, str]:
    parts = repository.split("/", 1)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise ValueError(f"invalid repository format: {repository!r}")
    return parts[0].strip(), parts[1].strip()


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


def sorted_labels(labels: list[str]) -> list[str]:
    return sorted(dict.fromkeys(labels))


def replace_label_set(labels: list[str], *, remove: set[str], add: set[str]) -> list[str]:
    output = [label for label in labels if label not in remove]
    output.extend(add)
    return sorted_labels(output)


def should_consider_for_reconcile(issue: dict[str, Any]) -> bool:
    if issue.get("state") not in (None, "open"):
        return False
    if "pull_request" in issue:
        return False

    labels = set(normalize_label_names(issue.get("labels", [])))
    if "backlog" not in labels:
        return False

    return any(priority in labels for priority in PRIORITY_RANK)


def extract_priority(labels: set[str]) -> str | None:
    ranked = [name for name in PRIORITY_RANK if name in labels]
    if not ranked:
        return None
    ranked.sort(key=lambda name: PRIORITY_RANK[name])
    return ranked[0]


def compute_reconcile_mutations(open_issues: list[dict[str, Any]]) -> tuple[str | None, list[ReconcileMutation]]:
    candidates: list[tuple[dict[str, Any], set[str], str]] = []

    for issue in open_issues:
        if not should_consider_for_reconcile(issue):
            continue

        labels = set(normalize_label_names(issue.get("labels", [])))
        priority = extract_priority(labels)
        if priority is None:
            continue
        candidates.append((issue, labels, priority))

    if not candidates:
        return None, []

    active_priority = min((priority for _, _, priority in candidates), key=lambda p: PRIORITY_RANK[p])
    mutations: list[ReconcileMutation] = []

    # deterministic order for stable reports/tests
    candidates.sort(key=lambda item: int(item[0].get("number", 0)))

    for issue, labels_set, priority in candidates:
        issue_number = int(issue["number"])
        current_labels = sorted_labels(list(labels_set))
        has_todo = "status:todo" in labels_set
        has_blocked = "status:blocked" in labels_set
        has_in_progress = "status:in-progress" in labels_set

        if priority == active_priority:
            if has_in_progress:
                target_labels = replace_label_set(
                    current_labels,
                    remove={"status:blocked", "status:todo"},
                    add={"status:in-progress"},
                )
                if target_labels != current_labels:
                    mutations.append(
                        ReconcileMutation(
                            issue_number=issue_number,
                            action="normalize_in_progress",
                            before_labels=current_labels,
                            after_labels=target_labels,
                        )
                    )
                continue

            if not has_todo or has_blocked:
                target_labels = replace_label_set(
                    current_labels,
                    remove={"status:blocked"},
                    add={"status:todo"},
                )
                if target_labels != current_labels:
                    mutations.append(
                        ReconcileMutation(
                            issue_number=issue_number,
                            action="promote_todo",
                            before_labels=current_labels,
                            after_labels=target_labels,
                        )
                    )
            continue

        # lower-priority tier => block if still todo
        if has_todo:
            target_labels = replace_label_set(
                current_labels,
                remove={"status:todo"},
                add={"status:blocked"},
            )
            if target_labels != current_labels:
                mutations.append(
                    ReconcileMutation(
                        issue_number=issue_number,
                        action="demote_blocked",
                        before_labels=current_labels,
                        after_labels=target_labels,
                        comment=DEMOTION_COMMENT_TEMPLATE.format(active_priority=active_priority),
                    )
                )

    return active_priority, mutations


def load_issues_snapshot(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("issues snapshot must be a JSON array")
    return raw


def save_issues_snapshot(path: Path, issues: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(issues, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def apply_mutations_to_snapshot(issues: list[dict[str, Any]], mutations: list[ReconcileMutation]) -> None:
    by_number = {int(issue.get("number")): issue for issue in issues if isinstance(issue, dict) and "number" in issue}

    for mutation in mutations:
        issue = by_number.get(mutation.issue_number)
        if not issue:
            continue

        issue["labels"] = list(mutation.after_labels)

        if mutation.comment:
            comments = issue.get("_comments")
            if not isinstance(comments, list):
                comments = []
            comments.append(mutation.comment)
            issue["_comments"] = comments


def dispatch_worker_claim_reconcile(
    repository: str,
    *,
    mode: str,
    issues_snapshot: Path | None,
    github_token_env: str,
    github_base_url: str,
    trigger_events: list[dict[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "repository": repository,
        "trigger_actions": sorted({event["action"] for event in trigger_events}),
        "trigger_deliveries": [event["delivery_id"] for event in trigger_events],
        "status": "skipped",
        "source": None,
        "active_priority": None,
        "mutation_count": 0,
        "mutations": [],
    }

    if mode != "apply":
        result["status"] = "dry-run"
        return result

    try:
        if issues_snapshot is not None:
            open_issues = load_issues_snapshot(issues_snapshot)
            result["source"] = "issues-snapshot"
        else:
            token = os.getenv(github_token_env, "").strip()
            if not token:
                result["status"] = "blocked_missing_github_token"
                result["reason"] = (
                    f"{github_token_env} is not set; set token or pass --issues-snapshot for local execution"
                )
                return result

            client = GitHubClient(token=token, base_url=github_base_url)
            open_issues = client.list_open_issues(repository)
            result["source"] = "github-api"

        active_priority, mutations = compute_reconcile_mutations(open_issues)
        result["active_priority"] = active_priority
        result["mutation_count"] = len(mutations)
        result["mutations"] = [
            {
                "issue_number": m.issue_number,
                "action": m.action,
                "before_labels": m.before_labels,
                "after_labels": m.after_labels,
                "comment": m.comment,
            }
            for m in mutations
        ]

        if issues_snapshot is not None:
            apply_mutations_to_snapshot(open_issues, mutations)
            save_issues_snapshot(issues_snapshot, open_issues)
        else:
            token = os.getenv(github_token_env, "").strip()
            client = GitHubClient(token=token, base_url=github_base_url)
            for mutation in mutations:
                client.set_issue_labels(repository, mutation.issue_number, mutation.after_labels)
                if mutation.comment:
                    client.create_issue_comment(repository, mutation.issue_number, mutation.comment)

        result["status"] = "reconcile_applied"
        return result

    except Exception as exc:  # pragma: no cover - mostly integration/network paths
        result["status"] = "dispatch_failed"
        result["reason"] = str(exc)
        return result


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
    lines.append(f"- reconcile_dispatch_requested: `{summary['reconcile_dispatch_requested']}`")
    lines.append(f"- reconcile_dispatch_runs: `{summary['reconcile_dispatch_runs']}`")
    lines.append(f"- reconcile_dispatch_failed: `{summary['reconcile_dispatch_failed']}`")
    lines.append(f"- reconcile_mutations: `{summary['reconcile_mutations']}`")
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
        if "dispatch" in event:
            lines.append(f"  - dispatch: `{event['dispatch']}`")

    lines.append("")
    lines.append("## Reconcile Dispatch")
    for dispatch in report.get("dispatches", []):
        lines.append("")
        lines.append(f"- repository `{dispatch['repository']}` · status `{dispatch['status']}`")
        lines.append(f"  - source: `{dispatch.get('source')}`")
        lines.append(f"  - active_priority: `{dispatch.get('active_priority')}`")
        lines.append(f"  - trigger_actions: `{', '.join(dispatch.get('trigger_actions', []))}`")
        lines.append(f"  - trigger_deliveries: `{', '.join(dispatch.get('trigger_deliveries', []))}`")
        lines.append(f"  - mutation_count: `{dispatch.get('mutation_count', 0)}`")
        if "reason" in dispatch:
            lines.append(f"  - reason: `{dispatch['reason']}`")

        for mutation in dispatch.get("mutations", []):
            lines.append(
                f"    - issue `#{mutation['issue_number']}` `{mutation['action']}`: "
                f"{mutation['before_labels']} -> {mutation['after_labels']}"
            )

    lines.append("")
    return "\n".join(lines)


def should_queue_reconcile_dispatch(event: dict[str, Any]) -> bool:
    return (
        event["event"] == "issues"
        and event["target_type"] == "issue"
        and event["action"] in RECONCILE_TRIGGER_ACTIONS
    )


def main() -> int:
    args = parse_args()

    queue_file = Path(args.queue_file)
    reports_root = Path(args.reports_root)
    state_file = Path(args.state_file)
    schema_path = Path(args.schema_path)
    issues_snapshot = Path(args.issues_snapshot) if args.issues_snapshot else None

    if not queue_file.is_file():
        print(f"queue file not found: {queue_file}", file=sys.stderr)
        return 2

    if not schema_path.is_file():
        print(f"schema file not found: {schema_path}", file=sys.stderr)
        return 2

    if args.max_events <= 0:
        print("--max-events must be > 0", file=sys.stderr)
        return 2

    if issues_snapshot is not None and not issues_snapshot.is_file():
        print(f"issues snapshot not found: {issues_snapshot}", file=sys.stderr)
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
    reconcile_batches: dict[str, dict[str, Any]] = {}

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

        event_record = {
            "line_no": line_no,
            "delivery_id": delivery_id,
            "status": "accepted",
            "route": route,
            "dispatch": "dry-run" if args.mode == "dry-run" else "accepted_no_dispatch",
        }

        if should_queue_reconcile_dispatch(normalized):
            if args.mode == "apply":
                batch = reconcile_batches.setdefault(
                    normalized["repository"],
                    {
                        "events": [],
                        "event_indices": [],
                    },
                )
                batch["events"].append(normalized)
                batch["event_indices"].append(len(events_out))
                event_record["dispatch"] = "queued:worker-claim-reconcile"
            else:
                event_record["dispatch"] = "would-queue:worker-claim-reconcile"

        events_out.append(event_record)

    save_state(state_file, state)

    dispatch_results: list[dict[str, Any]] = []
    for repository, batch in reconcile_batches.items():
        dispatch_result = dispatch_worker_claim_reconcile(
            repository,
            mode=args.mode,
            issues_snapshot=issues_snapshot,
            github_token_env=args.github_token_env,
            github_base_url=args.github_base_url,
            trigger_events=batch["events"],
        )
        dispatch_results.append(dispatch_result)

        dispatch_status = dispatch_result["status"]
        for idx in batch["event_indices"]:
            events_out[idx]["dispatch"] = dispatch_status

    finished = time.time()
    total = accepted + duplicates + invalid

    reconcile_dispatch_requested = sum(len(batch["events"]) for batch in reconcile_batches.values())
    reconcile_dispatch_runs = len(dispatch_results)
    reconcile_dispatch_failed = sum(
        1 for entry in dispatch_results if entry["status"] in {"dispatch_failed", "blocked_missing_github_token"}
    )
    reconcile_mutations = sum(int(entry.get("mutation_count", 0)) for entry in dispatch_results)

    exit_code = 4 if reconcile_dispatch_failed > 0 else 0
    status = "pass" if exit_code == 0 else "fail"

    report = {
        "job_id": "event-relay-consumer",
        "run_id": run_id,
        "mode": args.mode,
        "queue_file": str(queue_file),
        "schema_path": str(schema_path),
        "issues_snapshot": str(issues_snapshot) if issues_snapshot else None,
        "state_file": str(state_file),
        "started_at": format_utc(started),
        "finished_at": format_utc(finished),
        "duration_seconds": finished - started,
        "status": status,
        "exit_code": exit_code,
        "summary": {
            "total": total,
            "accepted": accepted,
            "duplicates": duplicates,
            "invalid": invalid,
            "pruned_state_entries": pruned_state_entries,
            "reconcile_dispatch_requested": reconcile_dispatch_requested,
            "reconcile_dispatch_runs": reconcile_dispatch_runs,
            "reconcile_dispatch_failed": reconcile_dispatch_failed,
            "reconcile_mutations": reconcile_mutations,
        },
        "events": events_out,
        "dispatches": dispatch_results,
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

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
