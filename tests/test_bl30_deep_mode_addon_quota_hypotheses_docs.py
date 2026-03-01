import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30DeepModeAddonQuotaHypothesesDocs(unittest.TestCase):
    def test_wp3_doc_exists_with_required_sections(self):
        doc_path = REPO_ROOT / "docs" / "DEEP_MODE_ADDON_QUOTA_HYPOTHESES_V1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/DEEP_MODE_ADDON_QUOTA_HYPOTHESES_V1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-30.3.wp3 — Deep-Mode Add-on-/Quota-Hypothesen + Transparenzrahmen (v1)",
            "## 1) Hypothesenblatt (messbar)",
            "## 2) Entitlement-/Quota-Kopplung an Contract-Felder",
            "## 3) Transparenzrahmen für AI-generierte Zusatzinhalte",
            "## 4) Entscheidungseingang für GTM-Track",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in wp3-Doku: {marker}")

        required_terms = [
            "DM-H1",
            "DM-H4",
            "options.capabilities.deep_mode.requested",
            "options.entitlements.deep_mode.quota_remaining",
            "result.status.capabilities.deep_mode.fallback_reason",
            "result.status.entitlements.deep_mode.quota_consumed",
            "#457",
            "#472",
            "#473",
            "GTM-IN-30.3-001",
        ]
        for term in required_terms:
            self.assertIn(term, content, msg=f"Pflichtbegriff fehlt in wp3-Doku: {term}")

    def test_contract_references_wp3_doc(self):
        contract_doc = (REPO_ROOT / "docs" / "api" / "contract-v1.md").read_text(encoding="utf-8")
        self.assertIn(
            "[`docs/DEEP_MODE_ADDON_QUOTA_HYPOTHESES_V1.md`](../DEEP_MODE_ADDON_QUOTA_HYPOTHESES_V1.md)",
            contract_doc,
            msg="contract-v1 muss auf die wp3 Add-on-/Quota-Doku verlinken",
        )

    def test_gtm_decision_log_tracks_wp3_input(self):
        decision_log = (REPO_ROOT / "docs" / "testing" / "GTM_VALIDATION_DECISION_LOG.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("GTM-IN-30.3-001 (Input)", decision_log)
        self.assertIn("docs/DEEP_MODE_ADDON_QUOTA_HYPOTHESES_V1.md", decision_log)
        self.assertIn("#457", decision_log)

    def test_backlog_tracks_wp3_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn(
            "#470 — BL-30.3.wp3 Add-on-/Quota-Hypothesen + Transparenzrahmen ausarbeiten (abgeschlossen 2026-03-01)",
            backlog,
        )
        self.assertIn("tests/test_bl30_deep_mode_addon_quota_hypotheses_docs.py", backlog)


if __name__ == "__main__":
    unittest.main()
