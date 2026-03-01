#!/usr/bin/env python3
"""Synchronize docs/BACKLOG.md with GitHub issue state and Now/Next/Later lanes.

Features:
1) Sync checklist boxes (`- [ ] #123 ...`) from issue state (closed => [x], open => [ ])
2) Regenerate a Now/Next/Later board inside marker comments.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CHECKBOX_RE = re.compile(r"^(\s*-\s*\[)( |x)(\]\s+#(\d+)\b.*)$")
BOARD_START = "<!-- NOW_NEXT_LATER:START -->"
BOARD_END = "<!-- NOW_NEXT_LATER:END -->"

PRIORITY_ORDER = {"priority:P0": 0, "priority:P1": 1, "priority:P2": 2, "priority:P3": 3}


@dataclass
class SyncStats:
    checkbox_updates: int = 0
    board_updated: bool = False


def run_gh_json(args: list[str]) -> Any:
    completed = subprocess.run(
        ["./scripts/gha", *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


def issue_labels(issue: dict[str, Any]) -> set[str]:
    return {str(label.get("name") or "") for label in issue.get("labels") or []}


def issue_priority(labels: set[str]) -> int:
    for key, order in PRIORITY_ORDER.items():
        if key in labels:
            return order
    return 99


def issue_sort_key(issue: dict[str, Any]) -> tuple[int, str, int]:
    labels = issue_labels(issue)
    return (issue_priority(labels), str(issue.get("createdAt") or ""), int(issue.get("number") or 0))


def classify_lane(issue: dict[str, Any]) -> str | None:
    labels = issue_labels(issue)
    if "backlog" not in labels:
        return None
    if "status:blocked" in labels:
        return "later"

    active_worker = "worker-a-active" in labels or "worker-b-active" in labels
    if "status:in-progress" in labels or active_worker:
        return "now"

    if "status:todo" in labels:
        if "priority:P3" in labels:
            return "later"
        return "next"

    return None


def render_lane(title: str, issues: list[dict[str, Any]]) -> list[str]:
    lines = [f"### {title}"]
    if not issues:
        lines.append("- (leer)")
        return lines

    for issue in sorted(issues, key=issue_sort_key):
        labels = issue_labels(issue)
        priority = next((label for label in sorted(labels) if label.startswith("priority:")), "priority:?")
        status = next((label for label in sorted(labels) if label.startswith("status:")), "status:?")
        lines.append(
            f"- [#{issue['number']}]({issue['url']}) — {issue['title']} ({priority}, {status})"
        )
    return lines


def render_now_next_later_board(open_issues: list[dict[str, Any]]) -> str:
    lanes = {"now": [], "next": [], "later": []}
    for issue in open_issues:
        lane = classify_lane(issue)
        if lane:
            lanes[lane].append(issue)

    parts: list[str] = [
        "## Now / Next / Later (auto-synced)",
        "",
        "Regelwerk:",
        "- **Now:** aktive Arbeit (`status:in-progress` oder `worker-*-active`)",
        "- **Next:** unblocked `status:todo` (außer `priority:P3`)",
        "- **Later:** `status:blocked` oder `priority:P3`",
        "",
    ]
    parts.extend(render_lane("Now", lanes["now"]))
    parts.append("")
    parts.extend(render_lane("Next", lanes["next"]))
    parts.append("")
    parts.extend(render_lane("Later", lanes["later"]))
    parts.append("")
    return "\n".join(parts).rstrip()


def sync_checkboxes(backlog_text: str, issue_state_by_number: dict[int, str]) -> tuple[str, int]:
    updates = 0
    out_lines: list[str] = []
    for line in backlog_text.splitlines():
        match = CHECKBOX_RE.match(line)
        if not match:
            out_lines.append(line)
            continue

        issue_number = int(match.group(4))
        state = issue_state_by_number.get(issue_number)
        if state not in {"OPEN", "CLOSED"}:
            out_lines.append(line)
            continue

        target_mark = "x" if state == "CLOSED" else " "
        if match.group(2) != target_mark:
            updates += 1
        out_lines.append(f"{match.group(1)}{target_mark}{match.group(3)}")

    return "\n".join(out_lines) + "\n", updates


def replace_between_markers(text: str, start_marker: str, end_marker: str, replacement: str) -> tuple[str, bool]:
    start = text.find(start_marker)
    end = text.find(end_marker)
    if start == -1 or end == -1 or end < start:
        raise ValueError("Now/Next/Later markers not found in backlog file")

    end += len(end_marker)
    block = f"{start_marker}\n{replacement}\n{end_marker}"
    updated = text[:start] + block + text[end:]
    return updated, updated != text


def sync_backlog_text(backlog_text: str, *, issues_all: list[dict[str, Any]], issues_open: list[dict[str, Any]]) -> tuple[str, SyncStats]:
    issue_state_by_number = {int(issue["number"]): str(issue.get("state") or "") for issue in issues_all}
    synced_text, checkbox_updates = sync_checkboxes(backlog_text, issue_state_by_number)

    board = render_now_next_later_board(issues_open)
    synced_text, board_updated = replace_between_markers(synced_text, BOARD_START, BOARD_END, board)

    return synced_text, SyncStats(checkbox_updates=checkbox_updates, board_updated=board_updated)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync BACKLOG checkboxes + Now/Next/Later board")
    parser.add_argument("--backlog-file", default="docs/BACKLOG.md")
    parser.add_argument("--write", action="store_true", help="Write changes to file")
    parser.add_argument("--print", action="store_true", dest="print_output", help="Print synced output")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    backlog_path = Path(args.backlog_file)
    backlog_text = backlog_path.read_text(encoding="utf-8")

    issues_all = run_gh_json(["issue", "list", "--state", "all", "--limit", "500", "--json", "number,state"])
    issues_open = run_gh_json(
        [
            "issue",
            "list",
            "--state",
            "open",
            "--limit",
            "500",
            "--json",
            "number,title,createdAt,labels,url,state",
        ]
    )

    synced_text, stats = sync_backlog_text(backlog_text, issues_all=issues_all, issues_open=issues_open)

    changed = synced_text != backlog_text
    if args.print_output:
        print(synced_text)

    if args.write and changed:
        backlog_path.write_text(synced_text, encoding="utf-8")

    print(
        json.dumps(
            {
                "changed": changed,
                "checkbox_updates": stats.checkbox_updates,
                "board_updated": stats.board_updated,
                "path": str(backlog_path),
            },
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
