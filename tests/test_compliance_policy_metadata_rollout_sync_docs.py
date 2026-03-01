import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestCompliancePolicyMetadataRolloutSyncDocs(unittest.TestCase):
    def test_contract_doc_contains_rollout_guidance_markers(self):
        doc_path = REPO_ROOT / "docs" / "compliance" / "POLICY_METADATA_CONTRACT_V1.md"
        self.assertTrue(doc_path.is_file(), msg="Policy-Metadaten-Contract fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "## Betriebs-/Rollout-Hinweise (v1)",
            "Policy-Änderung vorbereiten",
            "Lokale Validierung durchführen",
            "Doku-/Backlog-Sync sicherstellen",
            "tests/test_compliance_policy_metadata_rollout_sync_docs.py",
            "Merge-Gate",
        ]

        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Rollout-Marker fehlt: {marker}")

    def test_backlog_tracks_issue_540_and_parent_519_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("### BL-342 — Minimum-Compliance-Set (Governance-Rollout)", backlog)
        self.assertIn(
            "#519 — Datenmodell erweitern: Policy-Versionierung + Metadatenfelder (über #538/#539/#540 abgeschlossen 2026-03-01)",
            backlog,
        )
        self.assertIn(
            "#540 — BL-342.wp5.wp3: Backlog-/Rollout-Sync für Policy-Metadatenmodell abschließen (abgeschlossen 2026-03-01)",
            backlog,
        )

    def test_acceptance_catalog_tracks_mcs_at_010_automation(self):
        catalog = (
            REPO_ROOT / "docs" / "compliance" / "ACCEPTANCE_TEST_CATALOG_V1.md"
        ).read_text(encoding="utf-8")
        self.assertIn("MCS-AT-010", catalog)
        self.assertIn(
            "tests/test_compliance_policy_metadata_rollout_sync_docs.py",
            catalog,
        )


if __name__ == "__main__":
    unittest.main()
