#!/usr/bin/env python3
"""Validate YAML syntax for all GitHub Actions workflow files.

This is intentionally syntax-focused (not a full GitHub Actions linter) so we can
fail fast on parse errors like broken indentation/heredoc blocks.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    workflows_dir = repo_root / ".github" / "workflows"

    workflow_files = sorted(
        [*workflows_dir.glob("*.yml"), *workflows_dir.glob("*.yaml")],
    )

    if not workflow_files:
        print("No workflow files found under .github/workflows")
        return 0

    failures: list[tuple[Path, str]] = []

    for workflow_file in workflow_files:
        try:
            yaml.safe_load(workflow_file.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            failures.append((workflow_file, str(exc)))

    if failures:
        print("Workflow YAML validation failed:")
        for workflow_file, err in failures:
            print(f"- {workflow_file.relative_to(repo_root)}")
            for line in err.splitlines():
                print(f"    {line}")
        return 1

    print(f"Workflow YAML validation passed ({len(workflow_files)} files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
