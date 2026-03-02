import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_scoring_golden_drift_report.py"


class TestScoringGoldenDriftReportScript(unittest.TestCase):
    def test_script_runs_and_emits_reports(self):
        self.assertTrue(SCRIPT.is_file(), msg=f"missing script: {SCRIPT}")

        out_dir = REPO_ROOT / "runtime" / "tmp_test_outputs" / "scoring_golden_drift"
        if out_dir.exists():
            # best-effort cleanup (avoid adding extra deps like shutil.rmtree errors)
            for child in out_dir.glob("*"):
                child.unlink(missing_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)

        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--out-dir",
                str(out_dir),
                "--no-fail-on-drift",
            ],
            cwd=str(REPO_ROOT),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=f"script failed (rc={proc.returncode})\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}",
        )

        json_reports = sorted(out_dir.glob("scoring_golden_drift_report.*.json"))
        md_reports = sorted(out_dir.glob("scoring_golden_drift_report.*.md"))
        self.assertTrue(json_reports, msg="expected at least one JSON report")
        self.assertTrue(md_reports, msg="expected at least one Markdown report")

        payload = json.loads(json_reports[-1].read_text(encoding="utf-8"))
        self.assertIn("generated_at", payload)
        self.assertIn("cases", payload)
        self.assertIsInstance(payload["cases"], list)
        self.assertGreater(len(payload["cases"]), 0)

        kinds = {case.get("kind") for case in payload["cases"] if isinstance(case, dict)}
        self.assertIn("worked-example", kinds)
        self.assertIn("personalized-runtime", kinds)

        for case in payload["cases"]:
            self.assertIsInstance(case, dict)
            self.assertIn("case_id", case)
            self.assertIn("summary", case)
            self.assertIn("drift", case["summary"], msg=f"missing drift flag for case {case.get('case_id')}")


if __name__ == "__main__":
    unittest.main()
