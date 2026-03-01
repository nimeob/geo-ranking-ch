import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestComplianceHoldGovernanceDocs(unittest.TestCase):
    def test_hold_governance_doc_exists_with_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "compliance" / "HOLD_GOVERNANCE_V1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/compliance/HOLD_GOVERNANCE_V1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# Minimum-Compliance-Set — Hold-Governance v1",
            "## Rollen- und Berechtigungsmatrix",
            "| `Compliance Lead` | ja | ja |",
            "## Verbindliche Entscheidungsregeln",
            "**Vier-Augen-Prinzip**",
            "## Entscheidungswege (Setzen/Aufheben)",
            "## Pflicht-Nachweise pro Hold-Entscheidung",
            "| `hold_reason` | ja |",
            "Issue #517",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in Hold-Governance: {marker}")

    def test_backlog_tracks_issue_517_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("### BL-342 — Minimum-Compliance-Set (Governance-Rollout)", backlog)
        self.assertIn(
            "#517 — Hold-Governance definieren (wer darf Hold setzen/aufheben) (abgeschlossen 2026-03-01)",
            backlog,
        )


if __name__ == "__main__":
    unittest.main()
