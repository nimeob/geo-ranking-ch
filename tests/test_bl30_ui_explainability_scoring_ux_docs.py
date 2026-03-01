import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30UiExplainabilityScoringUxDocs(unittest.TestCase):
    def test_explainability_scoring_ux_doc_exists_with_core_sections(self):
        doc_path = REPO_ROOT / "docs" / "gui" / "HTML5_UI_EXPLAINABILITY_SCORING_UX_STANDARDS_V1.md"
        self.assertTrue(
            doc_path.is_file(),
            msg="docs/gui/HTML5_UI_EXPLAINABILITY_SCORING_UX_STANDARDS_V1.md fehlt",
        )

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-30.4.wp4 — Explainability-/Scoring-UX-Standards v1 (Desktop + Tablet)",
            "## 1) UX-Grundsätze für Explainability und Scoring",
            "## 2) Visualisierungsnorm (Score + Explainability)",
            "## 3) Progressive Disclosure + Fehlermeldungsrichtlinien",
            "## 4) Accessibility-Mindestkriterien (v1)",
            "## 5) Responsiveness-Mindestkriterien (Desktop + Tablet)",
            "## 6) Abnahmecheckliste für UX-Review (v1)",
            "## 8) Definition-of-Done-Check (#482)",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in BL-30.4.wp4 Doku: {marker}")

        for required_term in [
            "Desktop",
            "Tablet",
            "progressive disclosure",
            "aria-live",
            "Keyboard",
            "WCAG",
            "request_id",
            "#108",
            "#6",
            "#127",
        ]:
            self.assertIn(required_term, content, msg=f"Pflichtbegriff fehlt in BL-30.4.wp4 Doku: {required_term}")

    def test_backlog_tracks_bl30_4_wp4_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn(
            "#482 — BL-30.4.wp4 Explainability-/Scoring-UX-Standards (Desktop+Tablet) (abgeschlossen 2026-03-01)",
            backlog,
        )
        self.assertIn(
            "[`docs/gui/HTML5_UI_EXPLAINABILITY_SCORING_UX_STANDARDS_V1.md`](gui/HTML5_UI_EXPLAINABILITY_SCORING_UX_STANDARDS_V1.md)",
            backlog,
        )
        self.assertIn("tests/test_bl30_ui_explainability_scoring_ux_docs.py", backlog)


if __name__ == "__main__":
    unittest.main()
