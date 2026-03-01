import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_staging_lite_promote_gate.py"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


class TestStagingLitePromoteGate(unittest.TestCase):
    def _run_gate(self, *, candidate: str, approved: str, smoke_command: str, artifact_dir: Path):
        result = subprocess.run(
            [
                "python3",
                str(SCRIPT_PATH),
                "--candidate-digest",
                candidate,
                "--approved-digest",
                approved,
                "--smoke-command",
                smoke_command,
                "--artifact-dir",
                str(artifact_dir),
            ],
            cwd=str(REPO_ROOT),
            text=True,
            capture_output=True,
        )

        latest_json = artifact_dir / "latest.json"
        self.assertTrue(latest_json.exists(), msg=f"latest artifact missing: {latest_json}")
        payload = json.loads(latest_json.read_text(encoding="utf-8"))
        return result, payload

    def test_digest_mismatch_aborts_without_running_smoke(self):
        with tempfile.TemporaryDirectory(prefix="staging-lite-gate-") as td:
            tmp = Path(td)
            marker = tmp / "smoke-ran.txt"
            smoke_script = tmp / "smoke.sh"
            _write_executable(
                smoke_script,
                f"#!/usr/bin/env bash\nset -euo pipefail\ntouch {marker}\nexit 0\n",
            )

            artifact_dir = tmp / "artifacts"
            result, payload = self._run_gate(
                candidate="sha256:candidate",
                approved="sha256:approved",
                smoke_command=str(smoke_script),
                artifact_dir=artifact_dir,
            )

            self.assertEqual(result.returncode, 10)
            self.assertEqual(payload["decision"], "abort")
            self.assertEqual(payload["reason"], "digest_mismatch")
            self.assertFalse(payload["digest_match"])
            self.assertIsNone(payload["smoke_exit_code"])
            self.assertFalse(marker.exists(), msg="smoke command must not run on digest mismatch")

    def test_smoke_failure_aborts_with_rollback_hints(self):
        with tempfile.TemporaryDirectory(prefix="staging-lite-gate-") as td:
            tmp = Path(td)
            smoke_script = tmp / "smoke-fail.sh"
            _write_executable(smoke_script, "#!/usr/bin/env bash\nset -euo pipefail\nexit 7\n")

            artifact_dir = tmp / "artifacts"
            result, payload = self._run_gate(
                candidate="sha256:same",
                approved="sha256:same",
                smoke_command=str(smoke_script),
                artifact_dir=artifact_dir,
            )

            self.assertEqual(result.returncode, 20)
            self.assertEqual(payload["decision"], "abort")
            self.assertEqual(payload["reason"], "smoke_failed")
            self.assertTrue(payload["digest_match"])
            self.assertEqual(payload["smoke_exit_code"], 7)
            rollback = payload.get("rollback_hints") or {}
            self.assertIn("docs/BL31_DEPLOY_ROLLBACK_RUNBOOK.md", rollback.get("runbook", ""))
            self.assertGreaterEqual(len(rollback.get("steps") or []), 2)

    def test_smoke_success_marks_promote_ready(self):
        with tempfile.TemporaryDirectory(prefix="staging-lite-gate-") as td:
            tmp = Path(td)
            smoke_script = tmp / "smoke-ok.sh"
            _write_executable(smoke_script, "#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n")

            artifact_dir = tmp / "artifacts"
            result, payload = self._run_gate(
                candidate="sha256:ready",
                approved="sha256:ready",
                smoke_command=str(smoke_script),
                artifact_dir=artifact_dir,
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(payload["decision"], "promote_ready")
            self.assertEqual(payload["reason"], "gate_passed")
            self.assertTrue(payload["digest_match"])
            self.assertEqual(payload["smoke_exit_code"], 0)


if __name__ == "__main__":
    unittest.main()
