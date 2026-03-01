#!/usr/bin/env python3
"""Run a reproducible staging-lite promote gate with digest + smoke checks.

Exit codes:
- 0  => promote_ready
- 10 => abort (digest mismatch)
- 20 => abort (smoke failed)
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class GateResult:
    decision: str
    reason: str
    exit_code: int
    digest_match: bool
    smoke_exit_code: int | None


def _utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _run_smoke(smoke_command: str) -> int:
    completed = subprocess.run(smoke_command, shell=True, executable="/bin/bash", text=True)
    return int(completed.returncode)


def _write_artifacts(*, artifact_dir: Path, payload: dict[str, Any], markdown: str) -> dict[str, str]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    history_dir = artifact_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    timestamp = str(payload["timestamp_utc"])
    history_json = history_dir / f"{timestamp}.json"
    history_md = history_dir / f"{timestamp}.md"
    latest_json = artifact_dir / "latest.json"
    latest_md = artifact_dir / "latest.md"

    serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    history_json.write_text(serialized, encoding="utf-8")
    latest_json.write_text(serialized, encoding="utf-8")

    history_md.write_text(markdown, encoding="utf-8")
    latest_md.write_text(markdown, encoding="utf-8")

    return {
        "history_json": str(history_json),
        "history_md": str(history_md),
        "latest_json": str(latest_json),
        "latest_md": str(latest_md),
    }


def _build_markdown(payload: dict[str, Any], artifact_paths: dict[str, str]) -> str:
    rollback = payload["rollback_hints"]
    lines = [
        f"# Staging-lite Promote Gate — {payload['timestamp_utc']}",
        "",
        f"- Decision: **{payload['decision']}**",
        f"- Reason: `{payload['reason']}`",
        f"- Candidate digest: `{payload['candidate_digest']}`",
        f"- Approved digest: `{payload['approved_digest']}`",
        f"- Digest match: `{payload['digest_match']}`",
        f"- Smoke command: `{payload['smoke_command']}`",
        f"- Smoke exit code: `{payload['smoke_exit_code']}`",
        "",
        "## Abort / Rollback Hinweise",
        f"- Runbook: `{rollback['runbook']}`",
    ]
    for step in rollback["steps"]:
        lines.append(f"- {step}")

    lines.extend(
        [
            "",
            "## Artefakte",
            f"- latest.json: `{artifact_paths['latest_json']}`",
            f"- latest.md: `{artifact_paths['latest_md']}`",
            f"- history.json: `{artifact_paths['history_json']}`",
            f"- history.md: `{artifact_paths['history_md']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def run_gate(*, candidate_digest: str, approved_digest: str, smoke_command: str) -> GateResult:
    digest_match = candidate_digest == approved_digest
    if not digest_match:
        return GateResult(
            decision="abort",
            reason="digest_mismatch",
            exit_code=10,
            digest_match=False,
            smoke_exit_code=None,
        )

    smoke_exit_code = _run_smoke(smoke_command)
    if smoke_exit_code != 0:
        return GateResult(
            decision="abort",
            reason="smoke_failed",
            exit_code=20,
            digest_match=True,
            smoke_exit_code=smoke_exit_code,
        )

    return GateResult(
        decision="promote_ready",
        reason="gate_passed",
        exit_code=0,
        digest_match=True,
        smoke_exit_code=0,
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run staging-lite promote gate checks")
    parser.add_argument("--candidate-digest", required=True, help="Digest planned for promotion")
    parser.add_argument("--approved-digest", required=True, help="Digest approved by release owner")
    parser.add_argument(
        "--smoke-command",
        required=True,
        help="Shell command executed as smoke gate (exit 0 required)",
    )
    parser.add_argument(
        "--artifact-dir",
        default="artifacts/staging-lite",
        help="Directory for gate artifacts (latest + history)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])

    candidate_digest = str(args.candidate_digest).strip()
    approved_digest = str(args.approved_digest).strip()
    smoke_command = str(args.smoke_command).strip()

    if not candidate_digest or not approved_digest:
        print("ERROR: candidate/approved digest must be non-empty", file=sys.stderr)
        return 2
    if not smoke_command:
        print("ERROR: smoke-command must be non-empty", file=sys.stderr)
        return 2

    result = run_gate(
        candidate_digest=candidate_digest,
        approved_digest=approved_digest,
        smoke_command=smoke_command,
    )

    payload: dict[str, Any] = {
        "timestamp_utc": _utc_ts(),
        "decision": result.decision,
        "reason": result.reason,
        "candidate_digest": candidate_digest,
        "approved_digest": approved_digest,
        "digest_match": result.digest_match,
        "smoke_command": smoke_command,
        "smoke_exit_code": result.smoke_exit_code,
        "rollback_hints": {
            "runbook": "docs/BL31_DEPLOY_ROLLBACK_RUNBOOK.md",
            "steps": [
                "Promote abbrechen; keine weitere Deployment-Aktion ausführen.",
                "Falls bereits teilweise ausgerollt: service-lokalen Rollback gemäß Runbook durchführen.",
                "Nach Rollback Pflicht-Smoke für API (/health) und UI (/healthz) erneut ausführen.",
            ],
        },
    }

    artifact_dir = Path(args.artifact_dir)
    placeholder_paths = {
        "history_json": str(artifact_dir / "history" / f"{payload['timestamp_utc']}.json"),
        "history_md": str(artifact_dir / "history" / f"{payload['timestamp_utc']}.md"),
        "latest_json": str(artifact_dir / "latest.json"),
        "latest_md": str(artifact_dir / "latest.md"),
    }
    markdown = _build_markdown(payload, placeholder_paths)
    artifact_paths = _write_artifacts(artifact_dir=artifact_dir, payload=payload, markdown=markdown)

    print(json.dumps({"decision": result.decision, "reason": result.reason, **artifact_paths}, ensure_ascii=False))
    if result.decision == "promote_ready":
        print("staging-lite promote gate: PASS")
    else:
        print("staging-lite promote gate: ABORT")

    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
