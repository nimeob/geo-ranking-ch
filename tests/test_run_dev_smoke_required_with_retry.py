from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_dev_smoke_required_with_retry.py"


def _write_fake_runner(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--profile')
parser.add_argument('--flow')
parser.add_argument('--output-json', required=True)
args = parser.parse_args()

state_file = Path(os.environ['FAKE_RUNNER_STATE_FILE'])
fail_attempts = int(os.environ.get('FAKE_RUNNER_FAIL_ATTEMPTS', '0'))
count = 0
if state_file.exists():
    count = int(state_file.read_text(encoding='utf-8').strip() or '0')
count += 1
state_file.write_text(str(count), encoding='utf-8')

is_fail = count <= fail_attempts
fail_reason = os.environ.get('FAKE_RUNNER_FAIL_REASON', 'command_failed')
payload = {
    'schema_version': 'deploy-smoke-report/v1',
    'runner': 'fake',
    'status': 'fail' if is_fail else 'pass',
    'reason': fail_reason if is_fail else 'ok',
    'checks': [
        {
            'name': 'pr-split-smoke',
            'status': 'fail' if is_fail else 'pass',
            'reason': fail_reason if is_fail else 'ok',
            'kind': 'smoke',
        }
    ],
}
output = Path(args.output_json)
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(payload), encoding='utf-8')
raise SystemExit(1 if is_fail else 0)
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _run_wrapper(
    tmpdir: str,
    fail_attempts: int,
    max_attempts: int = 2,
    max_retries: int | None = None,
    smoke_seed: str | None = None,
    fail_reason: str = "command_failed",
) -> subprocess.CompletedProcess[str]:
    fake_runner = Path(tmpdir) / "fake_runner.py"
    _write_fake_runner(fake_runner)

    out_json = Path(tmpdir) / "final.json"
    report_json = Path(tmpdir) / "retry.json"
    summary_md = Path(tmpdir) / "summary.md"
    state_file = Path(tmpdir) / "state.txt"

    env = {"PATH": os.environ.get("PATH", "")}
    env["FAKE_RUNNER_STATE_FILE"] = str(state_file)
    env["FAKE_RUNNER_FAIL_ATTEMPTS"] = str(fail_attempts)
    env["FAKE_RUNNER_FAIL_REASON"] = fail_reason
    env["GITHUB_RUN_ID"] = "987654321"
    env["GITHUB_RUN_ATTEMPT"] = "3"
    env["GITHUB_RUN_NUMBER"] = "77"
    env["GITHUB_WORKFLOW"] = "dev-smoke-required"
    env["GITHUB_JOB"] = "dev-smoke-required"
    env["GITHUB_SHA"] = "deadbeef"
    env["GITHUB_REPOSITORY"] = "nimeob/geo-ranking-ch"
    env["GITHUB_SERVER_URL"] = "https://github.com"
    if smoke_seed is not None:
        env["DEV_SMOKE_TEST_SEED"] = smoke_seed

    command = [
        "python3",
        str(SCRIPT),
        "--runner-script",
        str(fake_runner),
        "--output-json",
        str(out_json),
        "--report-json",
        str(report_json),
        "--summary-markdown",
        str(summary_md),
        "--retry-delay-seconds",
        "0",
    ]
    if max_retries is not None:
        command.extend(["--max-retries", str(max_retries)])
    else:
        command.extend(["--max-attempts", str(max_attempts)])

    return subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        env=env,
    )


def test_retry_wrapper_marks_flaky_candidate_with_build_context_on_retry_success() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        proc = _run_wrapper(tmpdir, fail_attempts=1, max_retries=1)
        assert proc.returncode == 0, proc.stderr

        payload = json.loads((Path(tmpdir) / "retry.json").read_text(encoding="utf-8"))
        assert payload["status"] == "pass"
        assert payload["summary"]["attempts_used"] == 2
        assert payload["summary"]["retried_checks"] == 1
        assert payload["summary"]["flaky_candidates"] == 1
        assert payload["tests"][0]["name"] == "pr-split-smoke"
        assert payload["tests"][0]["flaky_hint"]
        flaky_context = payload["tests"][0]["flaky_context"]
        assert flaky_context["build_context"]["run_id"] == "987654321"
        assert flaky_context["build_context"]["run_attempt"] == "3"
        assert flaky_context["build_context"]["run_url"].endswith("/actions/runs/987654321/attempts/3")


def test_retry_wrapper_single_pass_has_no_flaky_or_retried_counts() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        proc = _run_wrapper(tmpdir, fail_attempts=0, max_retries=1)
        assert proc.returncode == 0, proc.stderr

        payload = json.loads((Path(tmpdir) / "retry.json").read_text(encoding="utf-8"))
        assert payload["status"] == "pass"
        assert payload["summary"]["attempts_used"] == 1
        assert payload["summary"]["retried_checks"] == 0
        assert payload["summary"]["flaky_candidates"] == 0
        assert payload["retry_policy"]["max_retries"] == 1
        assert payload["retry_policy"]["max_attempts"] == 2


def test_retry_wrapper_returns_failure_when_retries_exhausted() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        proc = _run_wrapper(tmpdir, fail_attempts=5, max_retries=1)
        assert proc.returncode != 0

        payload = json.loads((Path(tmpdir) / "retry.json").read_text(encoding="utf-8"))
        assert payload["status"] == "fail"
        assert payload["reason"] == "retries_exhausted"
        assert payload["summary"]["attempts_used"] == 2
        assert payload["summary"]["flaky_candidates"] == 0
        assert payload["failed_checks_final"] == [{"name": "pr-split-smoke", "reason": "command_failed"}]

        summary = (Path(tmpdir) / "summary.md").read_text(encoding="utf-8")
        assert "### Failed checks (final attempt)" in summary
        assert "`pr-split-smoke` — cause: `command_failed`" in summary


def test_retry_wrapper_surfaces_specific_failure_reason_in_final_report() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        proc = _run_wrapper(
            tmpdir,
            fail_attempts=5,
            max_retries=1,
            fail_reason="error_path_request_id_body_mismatch",
        )
        assert proc.returncode != 0

        payload = json.loads((Path(tmpdir) / "retry.json").read_text(encoding="utf-8"))
        assert payload["status"] == "fail"
        assert payload["failed_checks_final"] == [
            {"name": "pr-split-smoke", "reason": "error_path_request_id_body_mismatch"}
        ]

        summary = (Path(tmpdir) / "summary.md").read_text(encoding="utf-8")
        assert "`pr-split-smoke` — cause: `error_path_request_id_body_mismatch`" in summary


def test_retry_wrapper_reports_smoke_seed_in_json_and_summary() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        proc = _run_wrapper(tmpdir, fail_attempts=0, max_retries=1, smoke_seed="dev-smoke-seed-xyz")
        assert proc.returncode == 0, proc.stderr

        payload = json.loads((Path(tmpdir) / "retry.json").read_text(encoding="utf-8"))
        assert payload["smoke_test_seed"] == "dev-smoke-seed-xyz"

        summary = (Path(tmpdir) / "summary.md").read_text(encoding="utf-8")
        assert "Deterministic seed: `dev-smoke-seed-xyz`" in summary


def test_retry_wrapper_rejects_more_than_one_retry() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        proc = _run_wrapper(tmpdir, fail_attempts=0, max_retries=2)
        assert proc.returncode == 2
        assert "max 1 retry in Dev-CI" in proc.stderr
