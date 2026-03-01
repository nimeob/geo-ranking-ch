import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30PricingTierMatrixDocs(unittest.TestCase):
    def test_pricing_tier_matrix_doc_exists_with_core_sections(self):
        doc_path = REPO_ROOT / "docs" / "PRICING_TIER_LIMIT_MATRIX_V1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/PRICING_TIER_LIMIT_MATRIX_V1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-30.1.wp1 — Pricing-Tier-/Limit-Matrix v1",
            "## Tier-Matrix v1 (Entwurf)",
            "## Capability-/Entitlement-Gates (BL-30.2 Übergabe)",
            "## Add-ons (v1-Parkplatz, noch nicht aktiv)",
            "## Guardrails / Nicht-Ziele",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in Pricing-Tier-Matrix: {marker}")

        for tier in ["**Free**", "**Pro**", "**Business**"]:
            self.assertIn(tier, content, msg=f"Tier fehlt in Matrix: {tier}")

    def test_packaging_pricing_hypotheses_links_to_tier_matrix(self):
        hypotheses_doc = (REPO_ROOT / "docs" / "PACKAGING_PRICING_HYPOTHESES.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "[`docs/PRICING_TIER_LIMIT_MATRIX_V1.md`](./PRICING_TIER_LIMIT_MATRIX_V1.md)",
            hypotheses_doc,
            msg="Packaging-/Pricing-Hypothesen müssen auf die BL-30.1 Tier-/Limit-Matrix verlinken",
        )

    def test_backlog_tracks_bl30_wp1_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("### BL-30 — Monetization/Packaging/Deep-Mode/HTML5/Map/Mobile", backlog)
        self.assertIn(
            "#458 — BL-30.1.wp1 Pricing-Tier-/Limit-Matrix v1 inkl. Capability-Gates (abgeschlossen 2026-03-01)",
            backlog,
        )


if __name__ == "__main__":
    unittest.main()
