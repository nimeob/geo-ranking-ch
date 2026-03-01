import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30PricingValidationExperimentCardsDocs(unittest.TestCase):
    def test_experiment_cards_doc_exists_with_core_sections(self):
        doc_path = REPO_ROOT / "docs" / "PRICING_VALIDATION_EXPERIMENT_CARDS_V1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/PRICING_VALIDATION_EXPERIMENT_CARDS_V1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-30.1.wp3 — Preisvalidierungs-Experimentkarten + Entscheidungslogik (v1)",
            "## Inputs, Outputs und Run-Konvention",
            "## Experimentkarte 1 — CAND-API-PRO-390",
            "## Experimentkarte 2 — CAND-BIZ-API-890",
            "## Experimentkarte 3 — CAND-GUI-TEAM-590",
            "## Standardisierte Entscheidungslogik (Go / Adjust / Stop)",
            "## BL-30.1/BL-30.2 Ableitungsregel",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in WP3-Doku: {marker}")

        for required_term in ["GO", "ADJUST", "STOP", "candidate_id", "follow_ups"]:
            self.assertIn(required_term, content, msg=f"Pflichtbegriff fehlt in WP3-Doku: {required_term}")

    def test_followup_issue_template_exists_and_mentions_required_labels(self):
        template_path = REPO_ROOT / "docs" / "testing" / "BL30_FOLLOWUP_ISSUE_TEMPLATE.md"
        self.assertTrue(
            template_path.is_file(),
            msg="docs/testing/BL30_FOLLOWUP_ISSUE_TEMPLATE.md fehlt",
        )

        template = template_path.read_text(encoding="utf-8")
        self.assertIn("## Pflicht-Labels", template)
        self.assertIn("`backlog`", template)
        self.assertIn("`status:todo`", template)
        self.assertIn("Template: BL-30.1 Follow-up", template)
        self.assertIn("Template: BL-30.2 Follow-up", template)

    def test_backlog_tracks_bl30_wp3_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("### BL-30 — Monetization/Packaging/Deep-Mode/HTML5/Map/Mobile", backlog)
        self.assertIn(
            "#460 — BL-30.1.wp3 Preisvalidierungs-Experimentkarten + Entscheidungslogik (abgeschlossen 2026-03-01)",
            backlog,
        )
        self.assertIn("**Nächster Schritt:** #461 (oldest-first, unblocked).", backlog)


if __name__ == "__main__":
    unittest.main()
