import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30Html5UiArchitectureDocs(unittest.TestCase):
    def test_html5_ui_architecture_doc_exists_with_core_sections(self):
        doc_path = REPO_ROOT / "docs" / "gui" / "HTML5_UI_ARCHITECTURE_V1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/gui/HTML5_UI_ARCHITECTURE_V1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-30.4.wp1 — HTML5-UI-Architektur v1 (ADR + Boundary-Guardrails)",
            "## Architektur-Entscheidung (v1)",
            "## Modulgrenzen und Ownership",
            "## State-Ownership und Render-Pfad (v1)",
            "## Forward-Compatibility-Guardrails (#6, #127)",
            "## Nicht-Ziele (wp1)",
            "## Definition-of-Done-Check (#479)",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in BL-30.4.wp1 Doku: {marker}")

        for required_term in ["#480", "#481", "#482", "src/ui", "src/api", "src/shared"]:
            self.assertIn(required_term, content, msg=f"Pflichtbegriff fehlt in BL-30.4.wp1 Doku: {required_term}")

    def test_backlog_tracks_bl30_4_wp1_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn(
            "#479 — BL-30.4.wp1 HTML5-UI-Architektur v1 (ADR + Boundary-Guardrails) (abgeschlossen 2026-03-01)",
            backlog,
        )
        self.assertIn(
            "[`docs/gui/HTML5_UI_ARCHITECTURE_V1.md`](gui/HTML5_UI_ARCHITECTURE_V1.md)",
            backlog,
        )
        self.assertIn("tests/test_bl30_html5_ui_architecture_docs.py", backlog)


if __name__ == "__main__":
    unittest.main()
