import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_bl31_app_api_monitoring_evidence.sh"


class TestBl31AppApiMonitoringEvidenceScript(unittest.TestCase):
    def _write_executable(self, path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)

    def _write_rollout_evidence(self, path: Path) -> None:
        payload = {
            "uiService": {
                "healthUrl": "http://127.0.0.1:18081/healthz",
            },
            "apiService": {
                "healthUrl": "http://127.0.0.1:18080/health",
            },
        }
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_combined_evidence_success_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            out_dir = tmp / "artifacts"
            rollout = out_dir / "20260228T000000Z-bl31-ui-ecs-rollout.json"
            out_dir.mkdir(parents=True, exist_ok=True)
            self._write_rollout_evidence(rollout)

            fake_smoke = tmp / "fake_smoke.sh"
            self._write_executable(
                fake_smoke,
                """#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY' "${BL31_OUTPUT_JSON}"
import json
import sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({
  "overall": {"status": "pass"},
  "checks": {
    "api_health": {"status": "pass"},
    "app_reachability": {"status": "pass"},
    "cors_baseline": {"status": "pass"}
  }
}), encoding="utf-8")
PY
echo "fake smoke ok"
""",
            )

            fake_monitoring = tmp / "fake_monitoring.sh"
            self._write_executable(
                fake_monitoring,
                """#!/usr/bin/env bash
set -euo pipefail
echo "fake monitoring ok"
exit 0
""",
            )

            env = os.environ.copy()
            env.update(
                {
                    "OUT_DIR": str(out_dir),
                    "BL31_ROLLOUT_EVIDENCE": str(rollout),
                    "SMOKE_SCRIPT": str(fake_smoke),
                    "MONITORING_SCRIPT": str(fake_monitoring),
                    "BL31_STRICT_CORS": "1",
                }
            )

            cp = subprocess.run(
                [str(SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)

            summaries = sorted(out_dir.glob("*-bl31-app-api-monitoring-evidence.json"))
            self.assertTrue(summaries, "expected summary artifact")
            payload = json.loads(summaries[-1].read_text(encoding="utf-8"))
            self.assertEqual(payload["overall"]["status"], "pass")
            self.assertEqual(payload["inputs"]["apiBaseUrl"], "http://127.0.0.1:18080")
            self.assertEqual(payload["inputs"]["appBaseUrl"], "http://127.0.0.1:18081")
            self.assertEqual(payload["inputs"]["corsOrigin"], "http://127.0.0.1:18081")

    def test_monitoring_warning_is_non_blocking_and_recorded(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            out_dir = tmp / "artifacts"
            rollout = out_dir / "20260228T000000Z-bl31-ui-ecs-rollout.json"
            out_dir.mkdir(parents=True, exist_ok=True)
            self._write_rollout_evidence(rollout)

            fake_smoke = tmp / "fake_smoke.sh"
            self._write_executable(
                fake_smoke,
                """#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY' "${BL31_OUTPUT_JSON}"
import json
import sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({"overall": {"status": "pass"}}), encoding="utf-8")
PY
""",
            )

            fake_monitoring = tmp / "fake_monitoring.sh"
            self._write_executable(
                fake_monitoring,
                """#!/usr/bin/env bash
set -euo pipefail
echo "warning"
exit 10
""",
            )

            env = os.environ.copy()
            env.update(
                {
                    "OUT_DIR": str(out_dir),
                    "BL31_ROLLOUT_EVIDENCE": str(rollout),
                    "SMOKE_SCRIPT": str(fake_smoke),
                    "MONITORING_SCRIPT": str(fake_monitoring),
                }
            )

            cp = subprocess.run(
                [str(SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)

            summaries = sorted(out_dir.glob("*-bl31-app-api-monitoring-evidence.json"))
            payload = json.loads(summaries[-1].read_text(encoding="utf-8"))
            self.assertEqual(payload["overall"]["status"], "warn")

    def test_fails_fast_when_rollout_evidence_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            out_dir = tmp / "artifacts"
            out_dir.mkdir(parents=True, exist_ok=True)

            env = os.environ.copy()
            env.update(
                {
                    "OUT_DIR": str(out_dir),
                    "BL31_ROLLOUT_EVIDENCE": str(out_dir / "missing.json"),
                }
            )

            cp = subprocess.run(
                [str(SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(cp.returncode, 3)
            self.assertIn("rollout evidence not found", cp.stderr)


if __name__ == "__main__":
    unittest.main()
