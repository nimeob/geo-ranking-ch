import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.api.async_jobs import AsyncJobStore


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_async_retention_cleanup.py"


def _build_fixture_store(store_path: Path) -> dict[str, str]:
    store = AsyncJobStore(store_file=store_path)

    terminal_job = store.create_job(
        request_payload={"query": "terminal", "options": {}},
        request_id="req-terminal",
        query="terminal",
        intelligence_mode="basic",
    )
    terminal_job_id = str(terminal_job["job_id"])
    store.transition_job(job_id=terminal_job_id, to_status="running", progress_percent=10)
    store.transition_job(job_id=terminal_job_id, to_status="completed", progress_percent=100)
    store.create_result(
        job_id=terminal_job_id,
        result_payload={"kind": "terminal"},
        result_kind="final",
    )

    active_job = store.create_job(
        request_payload={"query": "active", "options": {}},
        request_id="req-active",
        query="active",
        intelligence_mode="basic",
    )
    active_job_id = str(active_job["job_id"])
    store.transition_job(job_id=active_job_id, to_status="running", progress_percent=10)
    store.create_result(
        job_id=active_job_id,
        result_payload={"kind": "active"},
        result_kind="partial",
    )

    return {
        "terminal_job_id": terminal_job_id,
        "active_job_id": active_job_id,
    }


class TestRunAsyncRetentionCleanupScript(unittest.TestCase):
    def test_script_applies_cleanup_for_terminal_jobs_only(self):
        with tempfile.TemporaryDirectory(prefix="async-retention-script-") as tmpdir:
            store_path = Path(tmpdir) / "store.json"
            fixture = _build_fixture_store(store_path)
            output_path = Path(tmpdir) / "cleanup.json"

            cp = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--store-file",
                    str(store_path),
                    "--results-ttl-seconds",
                    "0",
                    "--events-ttl-seconds",
                    "0",
                    "--output-json",
                    str(output_path),
                ],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)

            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("runner"), "run_async_retention_cleanup.py")
            self.assertGreater(payload.get("results", {}).get("delete_count", 0), 0)
            self.assertGreater(payload.get("events", {}).get("delete_count", 0), 0)

            store = AsyncJobStore(store_file=store_path)
            self.assertEqual(len(store.list_results(fixture["terminal_job_id"])), 0)
            self.assertEqual(len(store.list_events(fixture["terminal_job_id"])), 0)
            self.assertEqual(len(store.list_results(fixture["active_job_id"])), 1)
            self.assertGreaterEqual(len(store.list_events(fixture["active_job_id"])), 2)

    def test_script_dry_run_keeps_data(self):
        with tempfile.TemporaryDirectory(prefix="async-retention-script-") as tmpdir:
            store_path = Path(tmpdir) / "store.json"
            fixture = _build_fixture_store(store_path)

            store_before = AsyncJobStore(store_file=store_path)
            before_terminal_results = len(store_before.list_results(fixture["terminal_job_id"]))
            before_terminal_events = len(store_before.list_events(fixture["terminal_job_id"]))

            cp = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--store-file",
                    str(store_path),
                    "--results-ttl-seconds",
                    "0",
                    "--events-ttl-seconds",
                    "0",
                    "--dry-run",
                ],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
            payload = json.loads(cp.stdout)
            self.assertTrue(payload.get("dry_run"))
            self.assertGreater(payload.get("results", {}).get("delete_count", 0), 0)
            self.assertGreater(payload.get("events", {}).get("delete_count", 0), 0)

            store_after = AsyncJobStore(store_file=store_path)
            self.assertEqual(len(store_after.list_results(fixture["terminal_job_id"])), before_terminal_results)
            self.assertEqual(len(store_after.list_events(fixture["terminal_job_id"])), before_terminal_events)


if __name__ == "__main__":
    unittest.main()
