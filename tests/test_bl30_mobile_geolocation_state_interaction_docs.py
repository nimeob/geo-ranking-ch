import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30MobileGeolocationStateInteractionDocs(unittest.TestCase):
    def test_mobile_state_interaction_doc_contains_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "gui" / "MOBILE_GEOLOCATION_STATE_INTERACTION_V1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/gui/MOBILE_GEOLOCATION_STATE_INTERACTION_V1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-30.6.wp2 — Mobile Geolocation State-/Interaction-Contract v1 (Permission/Retry/Offline)",
            "## 2) Zustandsmodell (Permission + Locate + Analyze)",
            "## 3) Event-/Trigger-Contract (Permission/Retry/Offline)",
            "## 4) Retry-, Timeout- und Offline-Regeln",
            "## 5) UX-/A11y-Mindestkriterien (Mobile)",
            "## 7) Definition-of-Done-Check (#503)",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in BL-30.6.wp2 Doku: {marker}")

        required_terms = [
            "permission_required",
            "permission_denied",
            "offline_fallback",
            "mobile.retry.analyze",
            "network_offline",
            "aria-live",
            "options.mobile_geolocation",
            "result.status.mobile_geolocation",
            "#504",
        ]
        for term in required_terms:
            self.assertIn(term, content, msg=f"Pflichtbegriff fehlt in BL-30.6.wp2 Doku: {term}")

    def test_gui_and_api_docs_reference_mobile_state_interaction_contract(self):
        gui_flow_doc = (REPO_ROOT / "docs" / "gui" / "GUI_MVP_STATE_FLOW.md").read_text(encoding="utf-8")
        self.assertIn("Spezifische BL-30.6-Referenzen:", gui_flow_doc)
        self.assertIn(
            "[`docs/gui/MOBILE_GEOLOCATION_STATE_INTERACTION_V1.md`](./MOBILE_GEOLOCATION_STATE_INTERACTION_V1.md)",
            gui_flow_doc,
        )

        mobile_contract_doc = (
            REPO_ROOT / "docs" / "api" / "mobile-live-geolocation-contract-v1.md"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "#503 — Mobile State-/Interaction-Contract für Permission/Retry/Offline",
            mobile_contract_doc,
        )
        self.assertIn(
            "[`docs/gui/MOBILE_GEOLOCATION_STATE_INTERACTION_V1.md`](../gui/MOBILE_GEOLOCATION_STATE_INTERACTION_V1.md)",
            mobile_contract_doc,
        )

        contract_doc = (REPO_ROOT / "docs" / "api" / "contract-v1.md").read_text(encoding="utf-8")
        self.assertIn(
            "[`docs/gui/MOBILE_GEOLOCATION_STATE_INTERACTION_V1.md`](../gui/MOBILE_GEOLOCATION_STATE_INTERACTION_V1.md)",
            contract_doc,
        )

    def test_backlog_tracks_bl30_6_wp2_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn(
            "#503 — BL-30.6.wp2 Mobile Geolocation State-/Interaction-Contract v1 (Permission/Retry/Offline) (abgeschlossen 2026-03-01)",
            backlog,
        )
        self.assertIn(
            "[`docs/gui/MOBILE_GEOLOCATION_STATE_INTERACTION_V1.md`](gui/MOBILE_GEOLOCATION_STATE_INTERACTION_V1.md)",
            backlog,
        )
        self.assertIn("tests/test_bl30_mobile_geolocation_state_interaction_docs.py", backlog)


if __name__ == "__main__":
    unittest.main()
