from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_bl17_oidc_assumerole_posture.sh"


class TestCheckBl17OidcAssumeRolePosture(unittest.TestCase):
    def _prepare_temp_repo(self, tmp_path: Path, aws_arn: str, audit_repo_rc: int, audit_runtime_rc: int) -> Path:
        scripts_dir = tmp_path / "scripts"
        workflows_dir = tmp_path / ".github" / "workflows"
        bin_dir = tmp_path / "bin"

        scripts_dir.mkdir(parents=True, exist_ok=True)
        workflows_dir.mkdir(parents=True, exist_ok=True)
        bin_dir.mkdir(parents=True, exist_ok=True)

        script_copy = scripts_dir / "check_bl17_oidc_assumerole_posture.sh"
        script_copy.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
        script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

        (workflows_dir / "deploy.yml").write_text(
            "permissions:\n"
            "  id-token: write\n"
            "jobs:\n"
            "  deploy:\n"
            "    steps:\n"
            "      - uses: aws-actions/configure-aws-credentials@v4\n",
            encoding="utf-8",
        )

        audit_repo = scripts_dir / "audit_legacy_aws_consumer_refs.sh"
        audit_repo.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f"exit {audit_repo_rc}\n",
            encoding="utf-8",
        )
        audit_repo.chmod(audit_repo.stat().st_mode | stat.S_IXUSR)

        audit_runtime = scripts_dir / "audit_legacy_runtime_consumers.sh"
        audit_runtime.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f"exit {audit_runtime_rc}\n",
            encoding="utf-8",
        )
        audit_runtime.chmod(audit_runtime.stat().st_mode | stat.S_IXUSR)

        aws_mock = bin_dir / "aws"
        aws_mock.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "if [[ \"$#\" -ge 2 && \"$1\" == \"sts\" && \"$2\" == \"get-caller-identity\" ]]; then\n"
            f"  printf '%s\\n' '{aws_arn}'\n"
            "  exit 0\n"
            "fi\n"
            "echo 'unexpected aws invocation' >&2\n"
            "exit 99\n",
            encoding="utf-8",
        )
        aws_mock.chmod(aws_mock.stat().st_mode | stat.S_IXUSR)

        return script_copy

    def test_report_export_via_flag_contains_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script_copy = self._prepare_temp_repo(
                tmp_path,
                aws_arn="arn:aws:sts::523234426229:assumed-role/openclaw-ops-role/test-session",
                audit_repo_rc=10,
                audit_runtime_rc=30,
            )
            report_path = tmp_path / "artifacts" / "bl17-posture.json"

            env = os.environ.copy()
            env["PATH"] = f"{tmp_path / 'bin'}:{env['PATH']}"

            result = subprocess.run(
                [str(script_copy), "--report-json", str(report_path)],
                cwd=tmp_path,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue(report_path.is_file(), msg="Report file was not created")

            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["version"], 1)
            self.assertIn("generated_at_utc", report)
            self.assertEqual(
                report["caller"]["classification"],
                "assume-role-openclaw-ops-role",
            )
            self.assertEqual(
                report["exit_codes"]["audit_legacy_aws_consumer_refs"],
                10,
            )
            self.assertEqual(
                report["exit_codes"]["audit_legacy_runtime_consumers"],
                30,
            )
            self.assertEqual(report["exit_codes"]["final"], 0)

    def test_report_export_via_env_marks_legacy_caller_and_exit_30(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script_copy = self._prepare_temp_repo(
                tmp_path,
                aws_arn="arn:aws:iam::523234426229:user/swisstopo-api-deploy",
                audit_repo_rc=0,
                audit_runtime_rc=0,
            )
            report_path = tmp_path / "evidence" / "runtime-caller.json"

            env = os.environ.copy()
            env["PATH"] = f"{tmp_path / 'bin'}:{env['PATH']}"
            env["BL17_POSTURE_REPORT_JSON"] = str(report_path)

            result = subprocess.run(
                [str(script_copy)],
                cwd=tmp_path,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 30, msg=result.stderr)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(
                report["caller"]["classification"],
                "legacy-user-swisstopo-api-deploy",
            )
            self.assertEqual(report["exit_codes"]["caller_check"], 30)
            self.assertEqual(report["exit_codes"]["final"], 30)


if __name__ == "__main__":
    unittest.main()
