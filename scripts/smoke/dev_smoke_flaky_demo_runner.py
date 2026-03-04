#!/usr/bin/env python3
"""Deterministic flaky demo runner for Dev-CI retry reporting.

This script intentionally fails once and passes on the next attempt.
It mirrors the output contract of `scripts/run_deploy_smoke.py` minimally
so the retry wrapper can produce stable flaky markers in CI.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic flaky demo runner")
    parser.add_argument("--profile")
    parser.add_argument("--flow")
    parser.add_argument("--output-json", required=True)
    return parser.parse_args()


def _next_attempt(state_path: Path) -> int:
    count = 0
    if state_path.exists():
        raw = state_path.read_text(encoding="utf-8").strip()
        if raw:
            count = int(raw)
    count += 1
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(str(count), encoding="utf-8")
    return count


def main() -> int:
    args = _parse_args()

    state_file = Path(
        os.environ.get(
            "DEV_SMOKE_FLAKY_DEMO_STATE_FILE",
            "artifacts/dev-smoke-flaky-demo-state.txt",
        )
    )
    attempt_no = _next_attempt(state_file)
    should_fail = attempt_no == 1

    check_name = "flaky-demo-check"
    payload = {
        "schema_version": "deploy-smoke-report/v1",
        "runner": "dev-smoke-flaky-demo",
        "status": "fail" if should_fail else "pass",
        "reason": "demo_flaky_first_attempt" if should_fail else "ok",
        "checks": [
            {
                "name": check_name,
                "status": "fail" if should_fail else "pass",
                "reason": "demo_flaky_first_attempt" if should_fail else "ok",
                "kind": "smoke",
            }
        ],
    }

    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return 1 if should_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
