import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30UiStateInteractionContractDocs(unittest.TestCase):
    def test_state_interaction_contract_doc_exists_with_core_sections(self):
        doc_path = REPO_ROOT / "docs" / "gui" / "HTML5_UI_STATE_INTERACTION_CONTRACT_V1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/gui/HTML5_UI_STATE_INTERACTION_CONTRACT_V1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-30.4.wp2 — Zustandsmodell + Interaktions-Contract v1 (dynamische UI-Flows)",
            "## 1) Zustandsmodell (Analyze-Flow)",
            "## 2) Event-/Action-Contract (UI-Komponenten)",
            "## 3) Debounce-/Cancel-/Concurrency-Regeln",
            "## 4) Fehler-/Timeout-/Retry-Strategie pro State",
            "## 5) Additive Kompatibilität zu `POST /analyze`",
            "## 8) Definition-of-Done-Check (#480)",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in BL-30.4.wp2 Doku: {marker}")

        for required_term in [
            "ui.input.accepted",
            "ui.api.request.start",
            "ui.api.request.end",
            "AbortController",
            "X-Request-Id",
            "X-Session-Id",
            "src/shared/gui_mvp.py",
            "#481",
            "#482",
        ]:
            self.assertIn(required_term, content, msg=f"Pflichtbegriff fehlt in BL-30.4.wp2 Doku: {required_term}")

    def test_backlog_tracks_bl30_4_wp2_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn(
            "#480 — BL-30.4.wp2 Zustandsmodell + Interaktions-Contract für dynamische UI-Flows (abgeschlossen 2026-03-01)",
            backlog,
        )
        self.assertIn(
            "[`docs/gui/HTML5_UI_STATE_INTERACTION_CONTRACT_V1.md`](gui/HTML5_UI_STATE_INTERACTION_CONTRACT_V1.md)",
            backlog,
        )
        self.assertIn("tests/test_bl30_ui_state_interaction_contract_docs.py", backlog)


if __name__ == "__main__":
    unittest.main()
