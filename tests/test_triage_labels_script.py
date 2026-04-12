from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "triage_labels.sh"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR)


def _run_triage(tmp_path: Path, issues: list[dict]) -> subprocess.CompletedProcess[str]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)

    call_log = tmp_path / "gh-calls.log"
    edit_log = tmp_path / "gh-edits.log"

    gh_script = """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$GH_MOCK_CALL_LOG"
if [[ "${1:-}" == "issue" && "${2:-}" == "list" ]]; then
  printf '%s' "$GH_MOCK_ISSUES_JSON"
  exit 0
fi
if [[ "${1:-}" == "issue" && "${2:-}" == "edit" ]]; then
  printf '%s\n' "$*" >> "$GH_MOCK_EDIT_LOG"
  exit 0
fi
exit 1
"""
    _write_executable(fake_bin / "gh", gh_script)

    env = {
        "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}",
        "GH_MOCK_ISSUES_JSON": json.dumps(issues),
        "GH_MOCK_CALL_LOG": str(call_log),
        "GH_MOCK_EDIT_LOG": str(edit_log),
        "GITHUB_TOKEN": "test-token",
    }

    return subprocess.run(
        [str(SCRIPT)],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _extract_labels(edit_line: str) -> list[str]:
    tokens = edit_line.strip().split()
    labels: list[str] = []
    for idx, token in enumerate(tokens):
        if token == "--add-label" and idx + 1 < len(tokens):
            labels.append(tokens[idx + 1])
    return labels


def test_triage_labels_no_unlabeled_issues_exits_cleanly(tmp_path: Path) -> None:
    proc = _run_triage(
        tmp_path,
        issues=[
            {"number": 10, "title": "Already labeled", "labels": [{"name": "backlog"}]},
        ],
    )

    assert proc.returncode == 0, proc.stderr
    assert "NO_ZERO_LABEL_ISSUES" in proc.stdout

    edit_log = tmp_path / "gh-edits.log"
    assert not edit_log.exists() or edit_log.read_text(encoding="utf-8").strip() == ""


def test_triage_labels_applies_expected_labels_without_quote_artifacts(tmp_path: Path) -> None:
    proc = _run_triage(
        tmp_path,
        issues=[
            {"number": 11, "title": "[P1] UI bug: Login broken", "labels": []},
            {"number": 12, "title": "API docs update", "labels": []},
            {"number": 13, "title": "Already tagged", "labels": [{"name": "backlog"}]},
        ],
    )

    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert "SUMMARY_CHECKED:2" in proc.stdout
    assert "SUMMARY_LABELLED:2" in proc.stdout
    assert "LABELLED_ISSUES:11 12" in proc.stdout

    edit_log = (tmp_path / "gh-edits.log").read_text(encoding="utf-8").strip().splitlines()
    assert len(edit_log) == 2

    by_issue = {line.split()[2]: _extract_labels(line) for line in edit_log}

    assert set(by_issue["11"]) == {
        "backlog",
        "status:todo",
        "priority:P1",
        "bug",
        "area:ui",
    }
    assert set(by_issue["12"]) == {
        "backlog",
        "status:todo",
        "priority:P2",
        "documentation",
        "area:api",
    }

    # Regression guard: --add-label args must not carry literal quote chars.
    for line in edit_log:
        for token in line.split():
            assert '"' not in token
