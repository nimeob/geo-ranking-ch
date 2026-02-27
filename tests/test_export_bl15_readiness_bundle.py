from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "export_bl15_readiness_bundle.py"


class TestExportBl15ReadinessBundle(unittest.TestCase):
    def test_exports_bundle_with_required_and_optional_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir(parents=True, exist_ok=True)

            fingerprint_path = source_dir / "legacy-cloudtrail-fingerprint-report.json"
            fingerprint_path.write_text(
                json.dumps({"version": 1, "window_utc": {"start": "x", "end": "y"}}, indent=2) + "\n",
                encoding="utf-8",
            )

            consumer_inventory_path = source_dir / "LEGACY_CONSUMER_INVENTORY.md"
            consumer_inventory_path.write_text(
                "\n".join(
                    [
                        "# Consumer Inventory",
                        "",
                        "| target_id | owner |",
                        "| --- | --- |",
                        "| `ext-runner-a` | Team A |",
                        "| `ext-runner-b` | Team B |",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            runbook_path = source_dir / "LEGACY_IAM_USER_READINESS.md"
            runbook_path.write_text("# Readiness\n\nrunbook\n", encoding="utf-8")

            optional_dir = source_dir / "optional"
            optional_dir.mkdir(parents=True, exist_ok=True)
            optional_report = optional_dir / "posture.json"
            optional_report.write_text(json.dumps({"ok": True}) + "\n", encoding="utf-8")

            output_root = tmp_path / "out"
            bundle_id = "20260227T050000Z"

            result = subprocess.run(
                [
                    str(SCRIPT),
                    "--output-root",
                    str(output_root),
                    "--bundle-id",
                    bundle_id,
                    "--fingerprint-report",
                    str(fingerprint_path),
                    "--consumer-inventory-doc",
                    str(consumer_inventory_path),
                    "--readiness-runbook",
                    str(runbook_path),
                    "--optional-glob",
                    str(optional_dir / "*.json"),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["status"], "ok")
            self.assertEqual(summary["bundle_id"], bundle_id)
            self.assertEqual(summary["optional_artifact_count"], 1)

            bundle_path = Path(summary["bundle_path"])
            self.assertTrue((bundle_path / "README.md").is_file())
            self.assertTrue((bundle_path / "inventory.json").is_file())
            self.assertTrue((bundle_path / "consumer_targets_hint.md").is_file())
            self.assertTrue(
                (bundle_path / "evidence/fingerprint/legacy-cloudtrail-fingerprint-report.json").is_file()
            )
            self.assertTrue((bundle_path / "evidence/optional/posture.json").is_file())

            inventory = json.loads((bundle_path / "inventory.json").read_text(encoding="utf-8"))
            self.assertTrue(inventory["checks"]["fingerprint_evidence_present"])
            self.assertTrue(inventory["checks"]["consumer_targets_hint_present"])
            self.assertIn("ext-runner-a", inventory["consumer_target_ids"])
            self.assertIn("ext-runner-b", inventory["consumer_target_ids"])

    def test_fails_when_required_artifact_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            consumer_inventory_path = tmp_path / "LEGACY_CONSUMER_INVENTORY.md"
            consumer_inventory_path.write_text("# empty\n", encoding="utf-8")

            runbook_path = tmp_path / "LEGACY_IAM_USER_READINESS.md"
            runbook_path.write_text("# runbook\n", encoding="utf-8")

            result = subprocess.run(
                [
                    str(SCRIPT),
                    "--output-root",
                    str(tmp_path / "out"),
                    "--bundle-id",
                    "20260227T050100Z",
                    "--fingerprint-report",
                    str(tmp_path / "missing.json"),
                    "--consumer-inventory-doc",
                    str(consumer_inventory_path),
                    "--readiness-runbook",
                    str(runbook_path),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("required artifact not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
