from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GUARD_SCRIPT = REPO_ROOT / "scripts" / "check_bl17_oidc_only_guard.py"


class TestCheckBl17OidcOnlyGuard(unittest.TestCase):
    def _prepare_temp_repo(
        self,
        tmp_path: Path,
        *,
        posture_exit: int,
        caller_classification: str,
        static_key_refs_found: bool,
        runtime_exit: int,
        runtime_risk_findings: int,
        runtime_risk_ids: list[str],
        cloudtrail_exit: int,
    ) -> tuple[Path, Path]:
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)

        guard_copy = scripts_dir / "check_bl17_oidc_only_guard.py"
        guard_copy.write_text(GUARD_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
        guard_copy.chmod(guard_copy.stat().st_mode | stat.S_IXUSR)

        posture_script = scripts_dir / "check_bl17_oidc_assumerole_posture.sh"
        posture_script.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "out=\"\"\n"
            "while [[ $# -gt 0 ]]; do\n"
            "  case \"$1\" in\n"
            "    --report-json) out=\"$2\"; shift 2 ;;\n"
            "    *) shift ;;\n"
            "  esac\n"
            "done\n"
            "mkdir -p \"$(dirname \"$out\")\"\n"
            "cat > \"$out\" <<'JSON'\n"
            + json.dumps(
                {
                    "version": 1,
                    "caller": {"classification": caller_classification},
                    "workflow": {"static_key_refs_found": static_key_refs_found},
                },
                indent=2,
                sort_keys=True,
            )
            + "\nJSON\n"
            f"exit {posture_exit}\n",
            encoding="utf-8",
        )
        posture_script.chmod(posture_script.stat().st_mode | stat.S_IXUSR)

        runtime_script = scripts_dir / "inventory_bl17_runtime_credential_paths.py"
        runtime_script.write_text(
            "#!/usr/bin/env python3\n"
            "from __future__ import annotations\n"
            "import argparse\n"
            "import json\n"
            "from pathlib import Path\n"
            "parser = argparse.ArgumentParser()\n"
            "parser.add_argument('--output-json', required=True)\n"
            "args = parser.parse_args()\n"
            f"report = {{'summary': {{'risk_findings': {runtime_risk_findings}, 'risk_ids': {json.dumps(runtime_risk_ids)}}}}}\n"
            "out = Path(args.output_json)\n"
            "out.parent.mkdir(parents=True, exist_ok=True)\n"
            "out.write_text(json.dumps(report), encoding='utf-8')\n"
            f"raise SystemExit({runtime_exit})\n",
            encoding="utf-8",
        )
        runtime_script.chmod(runtime_script.stat().st_mode | stat.S_IXUSR)

        cloudtrail_script = scripts_dir / "audit_legacy_cloudtrail_consumers.sh"
        cloudtrail_script.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "echo 'mock cloudtrail output'\n"
            f"exit {cloudtrail_exit}\n",
            encoding="utf-8",
        )
        cloudtrail_script.chmod(cloudtrail_script.stat().st_mode | stat.S_IXUSR)

        wrapper_marker = tmp_path / "wrapper_invocations.log"
        wrapper_script = scripts_dir / "openclaw_runtime_assumerole_exec.sh"
        wrapper_script.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f"printf '%s\\n' \"$*\" >> '{wrapper_marker}'\n"
            "exec \"$@\"\n",
            encoding="utf-8",
        )
        wrapper_script.chmod(wrapper_script.stat().st_mode | stat.S_IXUSR)

        return guard_copy, wrapper_marker

    def test_guard_reports_ok_when_all_checks_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            guard_copy, _ = self._prepare_temp_repo(
                tmp_path,
                posture_exit=0,
                caller_classification="assume-role-openclaw-ops-role",
                static_key_refs_found=False,
                runtime_exit=0,
                runtime_risk_findings=0,
                runtime_risk_ids=[],
                cloudtrail_exit=0,
            )
            output_path = tmp_path / "artifacts" / "bl17" / "guard.json"

            result = subprocess.run(
                [str(guard_copy), "--output-json", str(output_path)],
                cwd=tmp_path,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            report = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "ok")
            self.assertEqual(report["checks"]["posture"]["status"], "ok")
            self.assertEqual(report["checks"]["runtime_inventory"]["status"], "ok")
            self.assertEqual(report["checks"]["cloudtrail"]["status"], "ok")

    def test_guard_reports_fail_when_legacy_findings_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            guard_copy, _ = self._prepare_temp_repo(
                tmp_path,
                posture_exit=30,
                caller_classification="legacy-user-swisstopo-api-deploy",
                static_key_refs_found=False,
                runtime_exit=10,
                runtime_risk_findings=2,
                runtime_risk_ids=["runtime-caller-legacy-user", "runtime-env-static-keys"],
                cloudtrail_exit=10,
            )
            output_path = tmp_path / "artifacts" / "bl17" / "guard.json"

            result = subprocess.run(
                [str(guard_copy), "--output-json", str(output_path), "--cloudtrail-lookback-hours", "24"],
                cwd=tmp_path,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 10, msg=result.stderr)
            report = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "fail")
            self.assertEqual(report["checks"]["posture"]["status"], "fail")
            self.assertEqual(report["checks"]["runtime_inventory"]["status"], "fail")
            self.assertEqual(report["checks"]["cloudtrail"]["status"], "fail")
            self.assertIn("artifacts/bl17/legacy-cloudtrail-audit.log", report["evidence_paths"])

    def test_guard_assume_role_first_wraps_all_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            guard_copy, wrapper_marker = self._prepare_temp_repo(
                tmp_path,
                posture_exit=0,
                caller_classification="assume-role-openclaw-ops-role",
                static_key_refs_found=False,
                runtime_exit=0,
                runtime_risk_findings=0,
                runtime_risk_ids=[],
                cloudtrail_exit=0,
            )
            output_path = tmp_path / "artifacts" / "bl17" / "guard.json"

            result = subprocess.run(
                [str(guard_copy), "--output-json", str(output_path), "--assume-role-first"],
                cwd=tmp_path,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            report = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "ok")
            self.assertEqual(report["execution_mode"], "assume-role-first")

            marker_lines = wrapper_marker.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(marker_lines), 3)
            self.assertTrue(any("check_bl17_oidc_assumerole_posture.sh" in line for line in marker_lines))
            self.assertTrue(any("inventory_bl17_runtime_credential_paths.py" in line for line in marker_lines))
            self.assertTrue(any("audit_legacy_cloudtrail_consumers.sh" in line for line in marker_lines))


if __name__ == "__main__":
    unittest.main()
