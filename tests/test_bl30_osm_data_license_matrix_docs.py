import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30OsmDataLicenseMatrixDocs(unittest.TestCase):
    def test_data_license_matrix_doc_exists_with_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "gui" / "OSM_MAP_DATA_SOURCE_LICENSE_MATRIX_V1.md"
        self.assertTrue(
            doc_path.is_file(),
            msg="docs/gui/OSM_MAP_DATA_SOURCE_LICENSE_MATRIX_V1.md fehlt",
        )

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-30.5.wp2 — Datenquellen-/Lizenzmatrix für Map- und Bau-/Zufahrtslayer",
            "## Entscheidungsrahmen (v1)",
            "## 1) Datenklassen-Matrix (Map + Bau-/Zufahrtskontext)",
            "## 2) Compliance-Mindeststandard für BL-30.5",
            "## 3) Offene Risiken / Follow-ups",
            "## 4) Definition-of-Done-Check (#495)",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in BL-30.5.wp2 Doku: {marker}")

        for required_term in [
            "Basemap",
            "Gebäude-/Parzellennähe",
            "Topografie/Hangneigung",
            "Straßentyp/Zufahrtsrelevanz",
            "GO",
            "NEEDS_CLARIFICATION",
            "BLOCKED",
            "ODbL",
            "swisstopo/geo.admin.ch",
            "#498",
            "#496",
        ]:
            self.assertIn(
                required_term,
                content,
                msg=f"Pflichtbegriff fehlt in BL-30.5.wp2 Doku: {required_term}",
            )

    def test_backlog_tracks_bl30_5_wp2_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn(
            "#495 — BL-30.5.wp2 Datenquellen-/Lizenzmatrix für Map- und Bau-/Zufahrtslayer (abgeschlossen 2026-03-01)",
            backlog,
        )
        self.assertIn(
            "[`docs/gui/OSM_MAP_DATA_SOURCE_LICENSE_MATRIX_V1.md`](gui/OSM_MAP_DATA_SOURCE_LICENSE_MATRIX_V1.md)",
            backlog,
        )
        self.assertIn("tests/test_bl30_osm_data_license_matrix_docs.py", backlog)


if __name__ == "__main__":
    unittest.main()
