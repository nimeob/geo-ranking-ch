import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30DeepModeContractDocs(unittest.TestCase):
    def test_deep_mode_contract_doc_exists_with_core_sections(self):
        doc_path = REPO_ROOT / "docs" / "api" / "deep-mode-contract-v1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/api/deep-mode-contract-v1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-30.3.wp1 — Deep-Mode-Contract v1 (Request/Status/Fallback)",
            "## Request-Handshake (additiv)",
            "## Response-/Status-Semantik (additiv)",
            "## Deterministische Fallback-Matrix",
            "## Guardrails / Nicht-Ziele (wp1)",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in Deep-Mode-Contract-Doku: {marker}")

        for required_term in [
            "options.capabilities.deep_mode.requested",
            "result.status.capabilities.deep_mode.effective",
            "graceful downgrade",
            "#469",
            "#470",
        ]:
            self.assertIn(required_term, content, msg=f"Pflichtbegriff fehlt in Deep-Mode-Contract-Doku: {required_term}")

    def test_contract_v1_links_to_deep_mode_doc(self):
        contract_doc = (REPO_ROOT / "docs" / "api" / "contract-v1.md").read_text(encoding="utf-8")
        self.assertIn(
            "[`docs/api/deep-mode-contract-v1.md`](./deep-mode-contract-v1.md)",
            contract_doc,
            msg="contract-v1 muss auf den Deep-Mode-Contract v1 verlinken",
        )

    def test_backlog_tracks_bl30_wp1_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn(
            "#468 — BL-30.3.wp1 Deep-Mode-Contract v1 (Request/Status/Fallback) spezifizieren (abgeschlossen 2026-03-01)",
            backlog,
        )
        self.assertIn("tests/test_bl30_deep_mode_contract_docs.py", backlog)


if __name__ == "__main__":
    unittest.main()
