import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30OsmTileOdblComplianceDocs(unittest.TestCase):
    def test_compliance_decision_doc_exists_with_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "gui" / "OSM_TILE_ODBL_COMPLIANCE_DECISION_V1.md"
        self.assertTrue(
            doc_path.is_file(),
            msg="docs/gui/OSM_TILE_ODBL_COMPLIANCE_DECISION_V1.md fehlt",
        )

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-30.5.wp2.f1 — OSM-Tile-/ODbL-Compliance-Entscheid (v1)",
            "## 1) Verbindliche Tile-Betriebsstrategie (Decision v1)",
            "## 2) Last- und Caching-Regeln (Mindeststandard)",
            "## 3) ODbL-Weitergabemodell (Produced Work vs. Share-Alike)",
            "## 4) Attribution-Mindestanforderungen",
            "## 5) Umsetzungsfolgen (verbindlich)",
            "## 6) Definition-of-Done-Check (#498)",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in #498-Doku: {marker}")

        for required_term in [
            "tile.openstreetmap.org",
            "prod",
            "Public-OSM-Tile-Endpunkt",
            "professioneller OSM-kompatibler Tile-Provider",
            "self-hosted Tile-Stack",
            "Share-Alike",
            "Produced Work",
            "Attribution",
            "#496",
            "docs/DEPLOYMENT_AWS.md",
        ]:
            self.assertIn(required_term, content, msg=f"Pflichtbegriff fehlt in #498-Doku: {required_term}")

    def test_backlog_and_deployment_sync_include_issue_498(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn(
            "#498 — BL-30.5.wp2.f1 OSM-Tile-/ODbL-Compliance-Entscheid für produktiven Kartenbetrieb (abgeschlossen 2026-03-01)",
            backlog,
        )
        self.assertIn(
            "[`docs/gui/OSM_TILE_ODBL_COMPLIANCE_DECISION_V1.md`](gui/OSM_TILE_ODBL_COMPLIANCE_DECISION_V1.md)",
            backlog,
        )
        self.assertIn("tests/test_bl30_osm_tile_odbl_compliance_docs.py", backlog)

        deployment = (REPO_ROOT / "docs" / "DEPLOYMENT_AWS.md").read_text(encoding="utf-8")
        self.assertIn("### BL-30.5 Kartenbetrieb: OSM-Tile-/ODbL-Compliance (verbindlich)", deployment)
        self.assertIn("`prod` darf **nicht** direkt gegen `tile.openstreetmap.org` laufen.", deployment)


if __name__ == "__main__":
    unittest.main()
