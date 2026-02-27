import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_openclaw_migrated_job.py"


class TestRunOpenClawMigratedJob(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT_PATH), *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_rejects_unknown_job(self):
        completed = self._run("--job", "unknown-job")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("invalid choice", completed.stderr)

    def test_writes_reports_for_successful_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            run_id = "20260227T080000Z"
            completed = self._run(
                "--job",
                "contract-tests",
                "--reports-root",
                tmpdir,
                "--timestamp",
                run_id,
                "--command-override",
                "python3 -c \"print('ok-job')\"",
            )

            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            payload = json.loads(completed.stdout.strip())
            self.assertEqual(payload["status"], "pass")

            history_json = Path(payload["history_json"])
            history_md = Path(payload["history_md"])
            latest_json = Path(payload["latest_json"])
            latest_md = Path(payload["latest_md"])

            self.assertTrue(history_json.is_file())
            self.assertTrue(history_md.is_file())
            self.assertTrue(latest_json.is_file())
            self.assertTrue(latest_md.is_file())

            report = json.loads(history_json.read_text(encoding="utf-8"))
            self.assertEqual(report["run_id"], run_id)
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["exit_code"], 0)
            self.assertEqual(len(report["steps"]), 1)
            self.assertEqual(report["steps"][0]["status"], "pass")
            self.assertIn("ok-job", report["steps"][0]["stdout"])

    def test_propagates_non_zero_exit_code_and_marks_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            run_id = "20260227T080001Z"
            completed = self._run(
                "--job",
                "docs-quality",
                "--reports-root",
                tmpdir,
                "--timestamp",
                run_id,
                "--command-override",
                "python3 -c \"import sys; print('boom'); sys.exit(7)\"",
            )

            self.assertEqual(completed.returncode, 7, msg=completed.stderr)
            payload = json.loads(completed.stdout.strip())
            self.assertEqual(payload["status"], "fail")
            self.assertEqual(payload["exit_code"], 7)

            latest_report = json.loads(Path(payload["latest_json"]).read_text(encoding="utf-8"))
            self.assertEqual(latest_report["status"], "fail")
            self.assertEqual(latest_report["exit_code"], 7)
            self.assertEqual(latest_report["steps"][0]["exit_code"], 7)


if __name__ == "__main__":
    unittest.main()
