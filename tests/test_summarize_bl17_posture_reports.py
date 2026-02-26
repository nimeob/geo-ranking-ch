from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "summarize_bl17_posture_reports.py"


class TestSummarizeBl17PostureReports(unittest.TestCase):
    def _write_report(
        self,
        path: Path,
        *,
        generated_at_utc: str,
        classification: str,
        final_exit: int,
    ) -> None:
        payload = {
            "version": 1,
            "generated_at_utc": generated_at_utc,
            "caller": {
                "arn": "arn:aws:sts::523234426229:assumed-role/openclaw-ops-role/session",
                "classification": classification,
            },
            "workflow": {
                "workflow_files_found": True,
                "configure_aws_credentials_found": True,
                "id_token_write_found": True,
                "static_key_refs_found": False,
            },
            "exit_codes": {
                "final": final_exit,
                "workflow_check": 0,
                "caller_check": 0,
                "audit_legacy_aws_consumer_refs": 0,
                "audit_legacy_runtime_consumers": 0,
            },
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def test_ready_when_all_reports_are_assumerole_and_exit_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write_report(
                tmp_path / "r1.json",
                generated_at_utc="2026-02-26T20:00:00Z",
                classification="assume-role-openclaw-ops-role",
                final_exit=0,
            )
            self._write_report(
                tmp_path / "r2.json",
                generated_at_utc="2026-02-26T21:00:00Z",
                classification="assume-role-openclaw-ops-role",
                final_exit=0,
            )
            output_path = tmp_path / "summary" / "bl17-window.json"

            result = subprocess.run(
                [
                    str(SCRIPT),
                    "--glob",
                    str(tmp_path / "*.json"),
                    "--min-reports",
                    "2",
                    "--output-json",
                    str(output_path),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["recommended_status"], "ready")
            self.assertEqual(summary["recommended_exit_code"], 0)
            self.assertEqual(summary["legacy_observed_count"], 0)
            self.assertEqual(summary["input"]["report_count"], 2)
            self.assertTrue(output_path.is_file())

    def test_not_ready_when_legacy_classification_is_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write_report(
                tmp_path / "legacy.json",
                generated_at_utc="2026-02-26T20:00:00Z",
                classification="legacy-user-swisstopo-api-deploy",
                final_exit=30,
            )
            self._write_report(
                tmp_path / "ok.json",
                generated_at_utc="2026-02-26T21:00:00Z",
                classification="assume-role-openclaw-ops-role",
                final_exit=0,
            )

            result = subprocess.run(
                [str(SCRIPT), "--glob", str(tmp_path / "*.json")],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 10, msg=result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["recommended_status"], "not-ready")
            self.assertEqual(summary["legacy_observed_count"], 1)
            self.assertGreaterEqual(summary["max_final_exit"], 30)

    def test_invalid_json_input_returns_exit_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "broken.json").write_text("{not-json}\n", encoding="utf-8")

            result = subprocess.run(
                [str(SCRIPT), "--glob", str(tmp_path / "*.json")],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("Invalid JSON", result.stderr)


if __name__ == "__main__":
    unittest.main()
