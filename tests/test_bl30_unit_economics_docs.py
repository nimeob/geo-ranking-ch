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
        allowed_next_steps = [
            "**Nächster Schritt:** oldest-first nächstes unblocked BL-30-Leaf in #106/#113 identifizieren (ggf. zuerst atomisieren), da #498 abgeschlossen ist und #106-Childs (#465/#466) aktuell gate-blocked sind.",
            "**Nächster Schritt:** BL-30-Follow-up #600 (oldest-first innerhalb der #594-Child-Work-Packages) umsetzen; danach #601/#602 und anschließend Parent #594/#577 finalisieren.",
            "**Nächster Schritt:** BL-30-Follow-up #602 (oldest-first innerhalb der #594-Child-Work-Packages) umsetzen; danach Parent #594/#577 finalisieren.",
            "**Nächster Schritt:** keiner (BL-30 vollständig abgeschlossen).",
        ]
        self.assertTrue(
            any(marker in backlog for marker in allowed_next_steps),
            msg="BACKLOG.md sollte einen gültigen BL-30-Nächster-Schritt (historisch, Follow-up oder final abgeschlossen) enthalten.",
        )


if __name__ == "__main__":
    unittest.main()
