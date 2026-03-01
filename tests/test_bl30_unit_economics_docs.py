import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30UnitEconomicsDocs(unittest.TestCase):
    def test_unit_economics_doc_exists_with_core_sections(self):
        doc_path = REPO_ROOT / "docs" / "UNIT_ECONOMICS_HYPOTHESES_V1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/UNIT_ECONOMICS_HYPOTHESES_V1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-30.1.wp2 — Unit-Economics-Hypothesen je Tier/Segment (v1)",
            "## Rechenlogik (v1)",
            "## Annahmen pro Tier (Bandbreite)",
            "## Sensitivitätshebel (für WP3-Experimente)",
            "## Entscheidungsschwellen (Go / Adjust / Stop)",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in Unit-Economics-Doku: {marker}")

        for required_term in ["CAC_Payback_Monate", "| Free |", "| Pro |", "| Business |"]:
            self.assertIn(required_term, content, msg=f"Pflichtbegriff fehlt in Unit-Economics-Doku: {required_term}")

    def test_packaging_pricing_hypotheses_links_to_unit_economics_doc(self):
        hypotheses_doc = (REPO_ROOT / "docs" / "PACKAGING_PRICING_HYPOTHESES.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "[`docs/UNIT_ECONOMICS_HYPOTHESES_V1.md`](./UNIT_ECONOMICS_HYPOTHESES_V1.md)",
            hypotheses_doc,
            msg="Packaging-/Pricing-Hypothesen müssen auf das BL-30.1.wp2 Unit-Economics-Modell verlinken",
        )

    def test_backlog_tracks_bl30_wp2_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("### BL-30 — Monetization/Packaging/Deep-Mode/HTML5/Map/Mobile", backlog)
        self.assertIn(
            "#459 — BL-30.1.wp2 Unit-Economics-Hypothesen je Tier/Segment strukturieren (abgeschlossen 2026-03-01)",
            backlog,
        )
        self.assertIn("**Nächster Schritt:** #460 (oldest-first, unblocked).", backlog)


if __name__ == "__main__":
    unittest.main()
