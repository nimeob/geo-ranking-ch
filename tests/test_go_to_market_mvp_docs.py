import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestGoToMarketMvpDocs(unittest.TestCase):
    def test_gtm_doc_exists_with_required_sections(self):
        doc_path = REPO_ROOT / "docs" / "GO_TO_MARKET_MVP.md"
        self.assertTrue(doc_path.is_file(), msg="docs/GO_TO_MARKET_MVP.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-20.7.b — Go-to-Market Artefakte (MVP)",
            "## 1) Value Proposition (MVP)",
            "## 2) Scope (MVP) / Nicht-Scope",
            "## 4) Demo-Flow / Storyline (10–12 Minuten)",
            "## 5) Offene Risiken (als Follow-up-Issues)",
            "#36",
            "#37",
            "#38",
            "docs/DEMO_DATASET_CH.md",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in GO_TO_MARKET_MVP.md: {marker}")


if __name__ == "__main__":
    unittest.main()
