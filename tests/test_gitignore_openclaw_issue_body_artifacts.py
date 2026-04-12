from __future__ import annotations

import subprocess
from pathlib import Path


def test_gitignore_contains_openclaw_issue_body_ignore_contract() -> None:
    lines = Path(".gitignore").read_text(encoding="utf-8").splitlines()
    assert "/.openclaw/issue_*_body.md" in lines


def test_git_check_ignore_ignores_openclaw_issue_body_snapshots() -> None:
    probe = Path(".openclaw/issue_999999_body.md")
    probe.write_text("probe", encoding="utf-8")
    try:
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
        assert "issue_*_body.md" in completed.stdout
    finally:
        probe.unlink(missing_ok=True)


def test_git_check_ignore_ignores_local_tools_directory() -> None:
    probe = Path(".tools/gitignore-probe.txt")
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text("probe", encoding="utf-8")
    try:
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
        assert ".tools/" in completed.stdout
    finally:
        probe.unlink(missing_ok=True)


def test_git_check_ignore_ignores_nightworker_worktree_directory() -> None:
    probe = Path(".nightworker/gitignore-probe.txt")
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text("probe", encoding="utf-8")
    try:
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
        assert "/.nightworker/" in completed.stdout
    finally:
        probe.unlink(missing_ok=True)


def test_git_check_ignore_ignores_night_worker_worktree_directory() -> None:
    probe = Path(".night-worker/gitignore-probe.txt")
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text("probe", encoding="utf-8")
    try:
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
        assert "/.night-worker/" in completed.stdout
    finally:
        probe.unlink(missing_ok=True)


def test_git_check_ignore_ignores_root_local_worktree_runtime_dirs() -> None:
    probes = [
        (Path(".nightlock/gitignore-probe.txt"), "/.nightlock/"),
        (Path(".worktrees/gitignore-probe.txt"), "/.worktrees/"),
        (Path(".tmp/gitignore-probe.txt"), "/.tmp/"),
        (Path(".local/gitignore-probe.txt"), "/.local/"),
    ]

    for probe, marker in probes:
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_text("probe", encoding="utf-8")
        try:
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
            assert marker in completed.stdout
        finally:
            probe.unlink(missing_ok=True)


def test_git_check_ignore_ignores_root_tmp_label_triage_helper() -> None:
    probe = Path(".tmp_label_triage.sh")
    probe.write_text("#!/usr/bin/env bash\necho probe\n", encoding="utf-8")
    try:
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
        assert "/.tmp_label_triage.sh" in completed.stdout
    finally:
        probe.unlink(missing_ok=True)


def test_git_check_ignore_ignores_dev_smoke_evidence_artifacts() -> None:
    probe = Path("reports/evidence/dev-night-worker-probe.json")
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text('{"probe": true}\n', encoding="utf-8")
    try:
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
        assert "reports/evidence/dev-*.json" in completed.stdout
    finally:
        probe.unlink(missing_ok=True)


def test_git_check_ignore_ignores_webkit_issue_smoke_evidence_artifacts() -> None:
    probes = [
        (
            Path("reports/evidence/issue-999-webkit-smoke-20260412T220000Z.json"),
            "reports/evidence/issue-*-webkit-smoke-*.json",
        ),
        (
            Path("reports/evidence/issue-999-webkit-ios-20260412T220000Z.png"),
            "reports/evidence/issue-*-webkit-ios-*.png",
        ),
    ]

    for probe, marker in probes:
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_text("probe", encoding="utf-8")
        try:
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
            assert marker in completed.stdout
        finally:
            probe.unlink(missing_ok=True)


def test_git_check_ignore_ignores_local_run_triangulate_helper() -> None:
    probe = Path("run_triangulate.sh")
    probe.write_text("#!/usr/bin/env bash\necho probe\n", encoding="utf-8")
    try:
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
        assert "/run_triangulate.sh" in completed.stdout
    finally:
        probe.unlink(missing_ok=True)
