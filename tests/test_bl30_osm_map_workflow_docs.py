import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30OsmMapWorkflowDocs(unittest.TestCase):
    def test_workflow_doc_exists_with_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "gui" / "OSM_MAP_INTELLIGENCE_WORKFLOW_V1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/gui/OSM_MAP_INTELLIGENCE_WORKFLOW_V1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-30.5.wp1 — Karten-Workflow-Spec v1 (Map-Pick -> Analyze -> Result)",
            "## 1) End-to-End Workflow (v1)",
            "## 2) Request-/Response-Handshake (additiver Kartenpfad)",
            "## 3) UI-State- und Fehlerpfad-Regeln",
            "## 4) Additive Kompatibilität zu `POST /analyze`",
            "## 6) Offene Folgepunkte (explizit nicht Teil von wp1)",
            "## 7) Definition-of-Done-Check (#494)",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in BL-30.5.wp1 Doku: {marker}")

        for required_term in [
            "coordinates.lat",
            "coordinates.lon",
            "result.status",
            "result.data",
            "ui.api.request.start",
            "ui.api.request.end",
            "api.request.start",
            "api.request.end",
            "#495",
            "#496",
        ]:
            self.assertIn(required_term, content, msg=f"Pflichtbegriff fehlt in BL-30.5.wp1 Doku: {required_term}")

    def test_backlog_tracks_bl30_5_wp1_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn(
            "#494 — BL-30.5.wp1 Karten-Workflow-Spec v1 (Map-Pick -> Analyze -> Result) (abgeschlossen 2026-03-01)",
            backlog,
        )
        self.assertIn(
            "[`docs/gui/OSM_MAP_INTELLIGENCE_WORKFLOW_V1.md`](gui/OSM_MAP_INTELLIGENCE_WORKFLOW_V1.md)",
            backlog,
        )
        self.assertIn("tests/test_bl30_osm_map_workflow_docs.py", backlog)


if __name__ == "__main__":
    unittest.main()
