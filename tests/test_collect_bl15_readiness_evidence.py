from __future__ import annotations

import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "collect_bl15_readiness_evidence.py"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


class TestCollectBl15ReadinessEvidence(unittest.TestCase):
    def test_collector_returns_findings_and_writes_bundle_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mock_dir = tmp_path / "mock"
            mock_dir.mkdir(parents=True, exist_ok=True)

            repo_audit = mock_dir / "repo_audit.sh"
            _write_executable(
                repo_audit,
                "#!/usr/bin/env bash\n"
                "echo 'repo finding'\n"
                "exit 10\n",
            )

            runtime_audit = mock_dir / "runtime_audit.sh"
            _write_executable(
                runtime_audit,
                "#!/usr/bin/env bash\n"
                "echo 'runtime ok'\n"
                "exit 0\n",
            )

            cloudtrail_audit = mock_dir / "cloudtrail_audit.sh"
            _write_executable(
                cloudtrail_audit,
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    cat >"${FINGERPRINT_REPORT_JSON}" <<'JSON'
                    {"status":"found_events","counts":{"events_analyzed":2}}
                    JSON
                    echo 'cloudtrail finding payload generated'
                    exit 0
                    """
                ),
            )

            bundle_export = mock_dir / "bundle_export.py"
            _write_executable(
                bundle_export,
                textwrap.dedent(
                    """\
                    #!/usr/bin/env python3
                    import argparse
                    import json

                    parser = argparse.ArgumentParser()
                    parser.add_argument('--output-root')
                    parser.add_argument('--bundle-id')
                    parser.add_argument('--fingerprint-report')
                    parser.add_argument('--optional-glob', action='append', default=[])
                    parser.parse_known_args()

                    print(json.dumps({
                        "status": "ok",
                        "bundle_id": "test-bundle",
                        "bundle_path": "/tmp/fake-bundle"
                    }))
                    """
                ),
            )

            result = subprocess.run(
                [
                    str(SCRIPT),
                    "--output-dir",
                    str(tmp_path / "out"),
                    "--report-id",
                    "unit-test-findings",
                    "--fingerprint-report",
                    str(tmp_path / "out" / "fingerprint.json"),
                    "--repo-audit-script",
                    str(repo_audit),
                    "--runtime-audit-script",
                    str(runtime_audit),
                    "--cloudtrail-audit-script",
                    str(cloudtrail_audit),
                    "--bundle-export-script",
                    str(bundle_export),
                    "--bundle-output-root",
                    str(tmp_path / "bundles"),
                    "--bundle-id",
                    "unit-bundle",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 10, msg=result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["status"], "findings")
            self.assertEqual(summary["blockers"], 0)
            self.assertGreaterEqual(summary["findings"], 1)

            report_json = Path(summary["report_json"])
            self.assertTrue(report_json.is_file())
            report_payload = json.loads(report_json.read_text(encoding="utf-8"))
            self.assertEqual(report_payload["final_status"], "findings")
            self.assertEqual(report_payload["final_exit_code"], 10)
            self.assertEqual(report_payload["bundle_export"]["status"], "ok")
            self.assertEqual(report_payload["bundle_export"]["bundle_path"], "/tmp/fake-bundle")

    def test_collector_returns_blocker_for_cloudtrail_execution_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mock_dir = tmp_path / "mock"
            mock_dir.mkdir(parents=True, exist_ok=True)

            repo_audit = mock_dir / "repo_audit.sh"
            _write_executable(repo_audit, "#!/usr/bin/env bash\nexit 0\n")

            runtime_audit = mock_dir / "runtime_audit.sh"
            _write_executable(runtime_audit, "#!/usr/bin/env bash\nexit 0\n")

            cloudtrail_audit = mock_dir / "cloudtrail_audit.sh"
            _write_executable(
                cloudtrail_audit,
                "#!/usr/bin/env bash\n"
                "echo 'permission denied' >&2\n"
                "exit 20\n",
            )

            result = subprocess.run(
                [
                    str(SCRIPT),
                    "--output-dir",
                    str(tmp_path / "out"),
                    "--report-id",
                    "unit-test-blocker",
                    "--repo-audit-script",
                    str(repo_audit),
                    "--runtime-audit-script",
                    str(runtime_audit),
                    "--cloudtrail-audit-script",
                    str(cloudtrail_audit),
                    "--skip-bundle",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 20)
            self.assertIn("BLOCKER: cloudtrail_fingerprint_audit returned exit code 20", result.stderr)

            summary = json.loads(result.stdout)
            self.assertEqual(summary["status"], "blocker")
            self.assertGreaterEqual(summary["blockers"], 1)

            report_json = Path(summary["report_json"])
            payload = json.loads(report_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["final_status"], "blocker")
            self.assertEqual(payload["final_exit_code"], 20)


if __name__ == "__main__":
    unittest.main()
