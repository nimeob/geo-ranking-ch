import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestComplianceKorrekturRichtlinieDocs(unittest.TestCase):
    def test_korrektur_richtlinie_doc_exists_with_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "compliance" / "KORREKTUR_RICHTLINIE_V1.md"
        self.assertTrue(
            doc_path.is_file(),
            msg="docs/compliance/KORREKTUR_RICHTLINIE_V1.md fehlt",
        )

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# Minimum-Compliance-Set — Korrektur-Richtlinie v1",
            "## Verbindliche Regeln",
            "**Keine Überschreibung des Originals**",
            "**Korrekturen nur als neue Version**",
            "**Pflichtfeld `korrekturgrund`**",
            "## Pflichtfelder für Korrektur-Einträge",
            "| `korrekturgrund` | ja |",
            "## Kommunikation (Freigabe-Definition)",
            "Issue #516",
        ]
        for marker in required_markers:
            self.assertIn(
                marker,
                content,
                msg=f"Marker fehlt in Korrektur-Richtlinie: {marker}",
            )

    def test_backlog_tracks_issue_516_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("### BL-342 — Minimum-Compliance-Set (Governance-Rollout)", backlog)
        self.assertIn(
            "#516 — Korrektur-Richtlinie freigeben (nur neue Version + Pflichtfeld Grund) (abgeschlossen 2026-03-01)",
            backlog,
        )


if __name__ == "__main__":
    unittest.main()
