from __future__ import annotations

import subprocess
from pathlib import Path


def _assert_git_ignores_path(probe: Path, expected_rule_snippet: str) -> None:
    completed = subprocess.run(
        ["git", "check-ignore", "-v", str(probe)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, (
        f"expected {probe} to be ignored by git, got rc={completed.returncode}, "
        f"stdout={completed.stdout!r}, stderr={completed.stderr!r}"
    )
    assert expected_rule_snippet in completed.stdout


def test_gitignore_contains_openclaw_issue_body_ignore_contract() -> None:
    lines = Path(".gitignore").read_text(encoding="utf-8").splitlines()
    assert "/.openclaw/issue_*_body.md" in lines


def test_git_check_ignore_ignores_openclaw_issue_body_snapshots() -> None:
    probe = Path(".openclaw/issue_999999_body.md")
    probe.write_text("probe", encoding="utf-8")
    try:
        _assert_git_ignores_path(probe, "issue_*_body.md")
    finally:
        probe.unlink(missing_ok=True)


def test_git_check_ignore_ignores_local_tools_directory() -> None:
    probe = Path(".tools/gitignore-probe.txt")
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text("probe", encoding="utf-8")
    try:
        _assert_git_ignores_path(probe, ".tools/")
    finally:
        probe.unlink(missing_ok=True)


def test_git_check_ignore_ignores_nightworker_worktree_directory() -> None:
    probe = Path(".nightworker/gitignore-probe.txt")
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text("probe", encoding="utf-8")
    try:
        _assert_git_ignores_path(probe, "/.nightworker/")
    finally:
        probe.unlink(missing_ok=True)


def test_git_check_ignore_ignores_local_cache_directory() -> None:
    probe = Path(".local/gitignore-probe.txt")
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text("probe", encoding="utf-8")
    try:
        _assert_git_ignores_path(probe, "/.local/")
    finally:
        probe.unlink(missing_ok=True)


def test_git_check_ignore_ignores_local_tmp_directory() -> None:
    probe = Path(".tmp/gitignore-probe.txt")
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text("probe", encoding="utf-8")
    try:
        _assert_git_ignores_path(probe, "/.tmp/")
    finally:
        probe.unlink(missing_ok=True)


def test_git_check_ignore_ignores_local_worktrees_directory() -> None:
    probe = Path(".worktrees/gitignore-probe.txt")
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text("probe", encoding="utf-8")
    try:
        _assert_git_ignores_path(probe, "/.worktrees/")
    finally:
        probe.unlink(missing_ok=True)


def test_git_check_ignore_ignores_local_run_triangulate_helper() -> None:
    probe = Path("run_triangulate.sh")
    probe.write_text("#!/usr/bin/env bash\necho probe\n", encoding="utf-8")
    try:
        _assert_git_ignores_path(probe, "/run_triangulate.sh")
    finally:
        probe.unlink(missing_ok=True)
