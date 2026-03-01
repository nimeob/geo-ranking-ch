import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestComplianceExportDeleteControlPlanDocs(unittest.TestCase):
    def test_control_plan_doc_exists_with_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "compliance" / "EXPORT_DELETE_CONTROL_PLAN_V1.md"
        self.assertTrue(
            doc_path.is_file(),
            msg="docs/compliance/EXPORT_DELETE_CONTROL_PLAN_V1.md fehlt",
        )

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# Minimum-Compliance-Set — Kontrollplan Export/Löschung v1",
            "## Kontrollfrequenz (verbindlich)",
            "Export-Kontrolle (Standard)",
            "Löschlauf-Kontrolle (Standard)",
            "## Stichprobenregeln",
            "sampling_seed",
            "## Nachweisformat (verbindlich)",
            "control_evidence.json",
            "## Rollen, Freigabe und Eskalation",
            "Issue #518",
        ]
        for marker in required_markers:
            self.assertIn(
                marker,
                content,
                msg=f"Marker fehlt im Kontrollplan Export/Löschung: {marker}",
            )

    def test_backlog_tracks_issue_518_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("### BL-342 — Minimum-Compliance-Set (Governance-Rollout)", backlog)
        self.assertIn(
            "#518 — Kontrollplan für Export- und Löschprozesse definieren (abgeschlossen 2026-03-01)",
            backlog,
        )


if __name__ == "__main__":
    unittest.main()
