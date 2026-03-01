import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30MapSuitabilityResponseModelDocs(unittest.TestCase):
    def test_response_model_doc_exists_with_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "api" / "map-point-construction-access-response-model-v1.md"
        self.assertTrue(
            doc_path.is_file(),
            msg="docs/api/map-point-construction-access-response-model-v1.md fehlt",
        )

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-30.5.wp3 — Response-Modell v1 für Bau-/Zufahrtseignung (additiv)",
            "## 1) Zielbild und Contract-Einordnung",
            "## 2) Modulpfad im grouped Response-Contract",
            "## 3) V1-Feldmodell (normativ)",
            "## 4) Beispielpayload (v1, kompakt)",
            "## 5) Pflichtmarker: Explainability / Confidence / Source",
            "## 6) Follow-up-Pfade für Runtime-Implementierung",
            "## 7) Definition-of-Done-Check (#496)",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in BL-30.5.wp3 Doku: {marker}")

        for required_term in [
            "result.data.modules.map_site_suitability",
            "result.data.by_source.map_intelligence.data.module_ref",
            "result.status.source_health.map_intelligence",
            "result.status.source_meta.map_intelligence",
            "explainability",
            "confidence.score",
            "sources[].source",
            "#110",
            "#498",
        ]:
            self.assertIn(
                required_term,
                content,
                msg=f"Pflichtbegriff fehlt in BL-30.5.wp3 Doku: {required_term}",
            )

    def test_backlog_tracks_bl30_5_wp3_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn(
            "#496 — BL-30.5.wp3 Response-Modell v1 für Bau-/Zufahrtseignung (additiv) (abgeschlossen 2026-03-01)",
            backlog,
        )
        self.assertIn(
            "[`docs/api/map-point-construction-access-response-model-v1.md`](api/map-point-construction-access-response-model-v1.md)",
            backlog,
        )
        self.assertIn("tests/test_bl30_map_suitability_response_model_docs.py", backlog)


if __name__ == "__main__":
    unittest.main()
