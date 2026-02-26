from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "inventory_bl17_runtime_credential_paths.py"


class TestInventoryBl17RuntimeCredentialPaths(unittest.TestCase):
    def _prepare_temp_repo(self, tmp_path: Path, caller_arn: str) -> tuple[Path, Path]:
        scripts_dir = tmp_path / "scripts"
        bin_dir = tmp_path / "bin"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        bin_dir.mkdir(parents=True, exist_ok=True)

        script_copy = scripts_dir / "inventory_bl17_runtime_credential_paths.py"
        script_copy.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
        script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

        # Presence of the wrapper is part of the inventory evidence.
        wrapper = scripts_dir / "aws_exec_via_openclaw_ops.sh"
        wrapper.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)

        aws_mock = bin_dir / "aws"
        aws_mock.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "if [[ \"$#\" -ge 2 && \"$1\" == \"sts\" && \"$2\" == \"get-caller-identity\" ]]; then\n"
            f"  printf '%s\\n' '{caller_arn}'\n"
            "  exit 0\n"
            "fi\n"
            "exit 99\n",
            encoding="utf-8",
        )
        aws_mock.chmod(aws_mock.stat().st_mode | stat.S_IXUSR)

        return script_copy, bin_dir

    def test_detects_legacy_caller_and_static_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script_copy, bin_dir = self._prepare_temp_repo(
                tmp_path,
                caller_arn="arn:aws:iam::523234426229:user/swisstopo-api-deploy",
            )

            output_path = tmp_path / "artifacts" / "runtime-inventory.json"
            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}:{env['PATH']}"
            env["AWS_ACCESS_KEY_ID"] = "AKIAX1234567890ABCD"
            env["AWS_SECRET_ACCESS_KEY"] = "super-secret"

            result = subprocess.run(
                [str(script_copy), "--output-json", str(output_path)],
                cwd=tmp_path,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 10, msg=result.stderr)
            report = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(report["version"], 1)
            self.assertEqual(report["caller"]["classification"], "legacy-user-swisstopo-api-deploy")

            detections = {d["id"]: d for d in report["detections"]}
            self.assertTrue(detections["runtime-caller-legacy-user"]["detected"])
            self.assertTrue(detections["runtime-env-static-keys"]["detected"])
            self.assertIn("runtime-env-static-keys", report["summary"]["risk_ids"])

    def test_returns_zero_when_only_assumerole_path_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script_copy, bin_dir = self._prepare_temp_repo(
                tmp_path,
                caller_arn="arn:aws:sts::523234426229:assumed-role/openclaw-ops-role/test-session",
            )

            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}:{env['PATH']}"
            env.pop("AWS_ACCESS_KEY_ID", None)
            env.pop("AWS_SECRET_ACCESS_KEY", None)
            env.pop("AWS_SESSION_TOKEN", None)

            result = subprocess.run(
                [str(script_copy)],
                cwd=tmp_path,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["caller"]["classification"], "assume-role-openclaw-ops-role")
            detections = {d["id"]: d for d in report["detections"]}
            self.assertTrue(detections["assumerole-wrapper-available"]["detected"])
            self.assertEqual(report["summary"]["recommended_exit_code"], 0)

    def test_temporary_session_keys_are_not_reported_as_static(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script_copy, bin_dir = self._prepare_temp_repo(
                tmp_path,
                caller_arn="arn:aws:sts::523234426229:assumed-role/openclaw-ops-role/runtime-session",
            )

            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}:{env['PATH']}"
            env["AWS_ACCESS_KEY_ID"] = "ASIA1234567890ABCD"
            env["AWS_SECRET_ACCESS_KEY"] = "session-secret"
            env["AWS_SESSION_TOKEN"] = "session-token"

            result = subprocess.run(
                [str(script_copy)],
                cwd=tmp_path,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            report = json.loads(result.stdout)
            detections = {d["id"]: d for d in report["detections"]}
            self.assertFalse(detections["runtime-env-static-keys"]["detected"])
            self.assertTrue(detections["runtime-env-session-credentials"]["detected"])
            self.assertNotIn("runtime-env-static-keys", report["summary"]["risk_ids"])


if __name__ == "__main__":
    unittest.main()
