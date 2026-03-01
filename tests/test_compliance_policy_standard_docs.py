import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestCompliancePolicyStandardDocs(unittest.TestCase):
    def test_policy_standard_doc_exists_with_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "compliance" / "POLICY_STANDARD_V1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/compliance/POLICY_STANDARD_V1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# Minimum-Compliance-Set — Policy-Standard v1",
            "## Pflicht-Metadaten pro Policy",
            "| `version` | ja |",
            "| `begruendung` | ja |",
            "| `wirksam_ab` | ja |",
            "| `impact_summary` | ja |",
            "## Mindestregeln für Policy-Änderungen",
            "## Freigabe-Workflow (v1)",
            "## Referenzvorlage (Copy/Paste)",
            "Issue #515",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt im Policy-Standard: {marker}")

    def test_backlog_tracks_issue_515_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("### BL-342 — Minimum-Compliance-Set (Governance-Rollout)", backlog)
        self.assertIn(
            "#515 — Policy-Standard finalisieren (Version, Begründung, Wirksam-ab, Impact-Pflicht) (abgeschlossen 2026-03-01)",
            backlog,
        )


if __name__ == "__main__":
    unittest.main()
