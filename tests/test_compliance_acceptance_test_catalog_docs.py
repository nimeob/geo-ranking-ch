import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestComplianceAcceptanceTestCatalogDocs(unittest.TestCase):
    def test_acceptance_test_catalog_exists_with_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "compliance" / "ACCEPTANCE_TEST_CATALOG_V1.md"
        self.assertTrue(
            doc_path.is_file(),
            msg="docs/compliance/ACCEPTANCE_TEST_CATALOG_V1.md fehlt",
        )

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# Minimum-Compliance-Set — Abnahmetestkatalog v1",
            "## Testmatrix Muss-Kriterien (Go-Live)",
            "MCS-AT-001",
            "MCS-AT-010",
            "#515",
            "#516",
            "#517",
            "#518",
            "#524",
            "#525",
            "#526",
            "#538",
            "#539",
            "#540",
            "tests/test_compliance_policy_metadata_contract_docs.py",
            "tests/test_compliance_policy_metadata_rollout_sync_docs.py",
            "## Sign-off-Protokoll (verbindlich)",
            "reports/compliance/acceptance/<YYYY>/<MM>/<acceptance_run_id>/",
            "Issue #527",
        ]

        for marker in required_markers:
            self.assertIn(
                marker,
                content,
                msg=f"Marker fehlt im Abnahmetestkatalog: {marker}",
            )

    def test_backlog_tracks_issue_527_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("### BL-342 — Minimum-Compliance-Set (Governance-Rollout)", backlog)
        self.assertIn(
            "#527 — Abnahmetests für Minimum-Compliance-Set erstellen (abgeschlossen 2026-03-01)",
            backlog,
        )


if __name__ == "__main__":
    unittest.main()
