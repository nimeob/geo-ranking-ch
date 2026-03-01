import json
import unittest
from pathlib import Path

from src.compliance.policy_metadata import validate_policy_metadata


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "compliance" / "POLICY_METADATA_CONTRACT_V1.md"
EXAMPLES_DIR = REPO_ROOT / "docs" / "compliance" / "examples"


class TestCompliancePolicyMetadataContractDocs(unittest.TestCase):
    def test_contract_doc_exists_with_required_markers(self):
        self.assertTrue(
            DOC_PATH.is_file(),
            msg="docs/compliance/POLICY_METADATA_CONTRACT_V1.md fehlt",
        )

        content = DOC_PATH.read_text(encoding="utf-8")
        required_markers = [
            "# Minimum-Compliance-Set — Policy-Metadaten-Contract v1",
            "## Contract-Schema (v1)",
            "| `policy_id` | `string` |",
            "| `version` | `string` |",
            "| `begruendung` | `string` |",
            "| `wirksam_ab` | `string` |",
            "| `impact_referenz` | `string` |",
            "docs/compliance/examples/policy-metadata.v1.valid-url.json",
            "docs/compliance/examples/policy-metadata.v1.valid-issue-ref.json",
            "docs/compliance/examples/policy-metadata.v1.invalid-missing-impact-ref.json",
            "src/compliance/policy_metadata.py",
            "Issue #539",
        ]

        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt im Policy-Metadaten-Contract: {marker}")

    def test_valid_example_artifacts_pass_runtime_validation(self):
        valid_examples = [
            "policy-metadata.v1.valid-url.json",
            "policy-metadata.v1.valid-issue-ref.json",
        ]

        for filename in valid_examples:
            payload = json.loads((EXAMPLES_DIR / filename).read_text(encoding="utf-8"))
            normalized = validate_policy_metadata(payload)
            self.assertEqual(
                set(normalized.keys()),
                {"policy_id", "version", "begruendung", "wirksam_ab", "impact_referenz"},
            )
            self.assertEqual(normalized["policy_id"], payload["policy_id"])
            self.assertEqual(normalized["version"], payload["version"])
            self.assertEqual(normalized["wirksam_ab"], payload["wirksam_ab"])

    def test_invalid_example_artifact_is_rejected(self):
        payload = json.loads(
            (EXAMPLES_DIR / "policy-metadata.v1.invalid-missing-impact-ref.json").read_text(
                encoding="utf-8"
            )
        )

        with self.assertRaisesRegex(ValueError, "missing required field: impact_referenz"):
            validate_policy_metadata(payload)

    def test_backlog_tracks_issue_539_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("### BL-342 — Minimum-Compliance-Set (Governance-Rollout)", backlog)
        self.assertIn(
            "#539 — BL-342.wp5.wp2: Policy-Metadaten-Contract + Beispielartefakte dokumentieren (abgeschlossen 2026-03-01)",
            backlog,
        )


if __name__ == "__main__":
    unittest.main()
