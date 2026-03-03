#!/usr/bin/env python3
"""Benchmark deploy workflow runtime before/after a cutoff commit.

Issue: #993

This helper reads GitHub Actions workflow runs (via `gh run list`) and compares
run durations before vs. after a cutoff timestamp (typically the merge commit of
smoke-runner consolidation work).
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class WorkflowRun:
    run_id: int
    started_at: datetime
    updated_at: datetime
    head_sha: str
    conclusion: str
    event: str
    url: str

    @property
    def duration_seconds(self) -> float:
        delta = self.updated_at - self.started_at
        return max(delta.total_seconds(), 0.0)


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _fmt_seconds(value: float) -> str:
    minutes = int(value // 60)
    seconds = int(round(value % 60))
    return f"{minutes:02d}:{seconds:02d}"


def _cutoff_from_commit(commit: str) -> datetime:
    cmd = ["git", "show", "-s", "--format=%cI", commit]
    out = subprocess.check_output(cmd, text=True).strip()
    if not out:
        raise RuntimeError(f"Could not resolve commit timestamp for {commit}")
    return _parse_ts(out)


def _load_runs_from_gh(repo: str, workflow: str, limit: int) -> list[dict]:
    cmd = [
        "gh",
        "run",
        "list",
        "--repo",
        repo,
        "--workflow",
        workflow,
        "--limit",
        str(limit),
        "--json",
        "databaseId,startedAt,updatedAt,headSha,conclusion,event,url",
    ]
    out = subprocess.check_output(cmd, text=True)
    return json.loads(out)


def _normalize_runs(raw_runs: list[dict], *, conclusion: str | None, event: str | None) -> list[WorkflowRun]:
    runs: list[WorkflowRun] = []
    for item in raw_runs:
        item_conclusion = str(item.get("conclusion") or "").strip().lower()
        item_event = str(item.get("event") or "").strip().lower()

        if conclusion and item_conclusion != conclusion:
            continue
        if event and item_event != event:
            continue

        started_at = item.get("startedAt")
        updated_at = item.get("updatedAt")
        if not started_at or not updated_at:
            continue

        runs.append(
            WorkflowRun(
                run_id=int(item.get("databaseId") or 0),
                started_at=_parse_ts(str(started_at)),
                updated_at=_parse_ts(str(updated_at)),
                head_sha=str(item.get("headSha") or ""),
                conclusion=item_conclusion,
                event=item_event,
                url=str(item.get("url") or ""),
            )
        )

    runs.sort(key=lambda run: run.started_at)
    return runs


def _summarize(values: list[float]) -> dict[str, float]:
    if not values:
        return {"count": 0, "median": 0.0, "mean": 0.0, "min": 0.0, "max": 0.0}
    return {
        "count": float(len(values)),
        "median": float(statistics.median(values)),
        "mean": float(statistics.mean(values)),
        "min": float(min(values)),
        "max": float(max(values)),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare deploy workflow runtime before/after cutoff")
    parser.add_argument("--repo", default="nimeob/geo-ranking-ch", help="GitHub repository owner/name")
    parser.add_argument("--workflow", default="deploy.yml", help="Workflow file or name")
    parser.add_argument("--limit", type=int, default=120, help="Max workflow runs to fetch")
    parser.add_argument("--cutoff-sha", required=True, help="Commit SHA used as before/after cutoff")
    parser.add_argument(
        "--conclusion",
        default="success",
        choices=("success", "failure", "cancelled", "skipped", "startup_failure", "neutral", "timed_out", "action_required", ""),
        help="Filter by run conclusion (empty string disables filter)",
    )
    parser.add_argument(
        "--event",
        default="",
        help="Optional event filter (e.g. schedule or workflow_dispatch)",
    )
    parser.add_argument("--output-json", default="", help="Optional output path for JSON summary")
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    conclusion_filter = args.conclusion.strip().lower() or None
    event_filter = args.event.strip().lower() or None

    cutoff = _cutoff_from_commit(args.cutoff_sha)
    raw_runs = _load_runs_from_gh(args.repo, args.workflow, args.limit)
    runs = _normalize_runs(raw_runs, conclusion=conclusion_filter, event=event_filter)

    before = [run for run in runs if run.started_at < cutoff]
    after = [run for run in runs if run.started_at >= cutoff]

    before_durations = [run.duration_seconds for run in before]
    after_durations = [run.duration_seconds for run in after]

    before_stats = _summarize(before_durations)
    after_stats = _summarize(after_durations)

    improvement_seconds = before_stats["median"] - after_stats["median"]
    improvement_percent = 0.0
    if before_stats["median"] > 0:
        improvement_percent = (improvement_seconds / before_stats["median"]) * 100.0

    print("# Deploy Gate Runtime Benchmark")
    print()
    print(f"- repo: `{args.repo}`")
    print(f"- workflow: `{args.workflow}`")
    print(f"- cutoff_sha: `{args.cutoff_sha}`")
    print(f"- cutoff_time_utc: `{cutoff.isoformat().replace('+00:00', 'Z')}`")
    print(f"- filters: conclusion={conclusion_filter or 'none'}, event={event_filter or 'none'}")
    print()
    print("## Summary")
    print()
    print("| bucket | count | median | mean | min | max |")
    print("|---|---:|---:|---:|---:|---:|")
    print(
        "| before | {count:.0f} | {median} | {mean} | {min_} | {max_} |".format(
            count=before_stats["count"],
            median=_fmt_seconds(before_stats["median"]),
            mean=_fmt_seconds(before_stats["mean"]),
            min_=_fmt_seconds(before_stats["min"]),
            max_=_fmt_seconds(before_stats["max"]),
        )
    )
    print(
        "| after | {count:.0f} | {median} | {mean} | {min_} | {max_} |".format(
            count=after_stats["count"],
            median=_fmt_seconds(after_stats["median"]),
            mean=_fmt_seconds(after_stats["mean"]),
            min_=_fmt_seconds(after_stats["min"]),
            max_=_fmt_seconds(after_stats["max"]),
        )
    )
    print()
    print(
        "- median delta (before-after): {delta} ({pct:+.2f}%)".format(
            delta=_fmt_seconds(abs(improvement_seconds)),
            pct=improvement_percent,
        )
    )
    print()
    print("## Sample runs (latest 5 per bucket)")
    print()
    print("| bucket | run_id | started_at_utc | duration | head_sha | url |")
    print("|---|---:|---|---:|---|---|")

    for bucket_name, bucket_runs in (("before", before[-5:]), ("after", after[-5:])):
        for run in bucket_runs:
            print(
                f"| {bucket_name} | {run.run_id} | {run.started_at.isoformat().replace('+00:00', 'Z')} "
                f"| {_fmt_seconds(run.duration_seconds)} | `{run.head_sha[:7]}` | {run.url} |"
            )

    if args.output_json:
        payload = {
            "repo": args.repo,
            "workflow": args.workflow,
            "cutoff_sha": args.cutoff_sha,
            "cutoff_time_utc": cutoff.isoformat().replace("+00:00", "Z"),
            "filters": {
                "conclusion": conclusion_filter,
                "event": event_filter,
            },
            "summary": {
                "before": before_stats,
                "after": after_stats,
                "median_delta_seconds": improvement_seconds,
                "median_delta_percent": improvement_percent,
            },
            "before": [
                {
                    "run_id": run.run_id,
                    "started_at_utc": run.started_at.isoformat().replace("+00:00", "Z"),
                    "duration_seconds": run.duration_seconds,
                    "head_sha": run.head_sha,
                    "url": run.url,
                }
                for run in before
            ],
            "after": [
                {
                    "run_id": run.run_id,
                    "started_at_utc": run.started_at.isoformat().replace("+00:00", "Z"),
                    "duration_seconds": run.duration_seconds,
                    "head_sha": run.head_sha,
                    "url": run.url,
                }
                for run in after
            ],
        }
        out_path = Path(args.output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    if not before or not after:
        print("\nWARNING: One benchmark bucket is empty; collect more workflow runs for stronger confidence.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
