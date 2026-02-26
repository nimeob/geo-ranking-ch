import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestDataSourceFieldMappingDocs(unittest.TestCase):
    def test_mapping_doc_exists_with_required_sections_and_followups(self):
        doc_path = REPO_ROOT / "docs" / "DATA_SOURCE_FIELD_MAPPING_CH.md"
        self.assertTrue(doc_path.is_file(), msg="docs/DATA_SOURCE_FIELD_MAPPING_CH.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-20.2.b — Feld-Mapping Quelle -> Domain (CH, v1)",
            "## 2) Verbindliche Transform-/Normalisierungsregeln",
            "## 3.1 `geoadmin_search` (swisstopo SearchServer)",
            "## 3.3 `geoadmin_gwr` (BFS GWR über geo.admin)",
            "## 3.10 `osm_poi_overpass`",
            "## 5) Gaps / Follow-up-Issues",
            "#63",
            "#64",
            "#65",
        ]

        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in DATA_SOURCE_FIELD_MAPPING_CH.md: {marker}")


if __name__ == "__main__":
    unittest.main()
