import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30CloseoutDocs(unittest.TestCase):
    def test_closeout_doc_exists_with_core_sections(self):
        doc_path = REPO_ROOT / "docs" / "BL30_1_CLOSEOUT_V1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/BL30_1_CLOSEOUT_V1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-30.1.wp4 — Konsolidierter Abschluss + BL-30.2 Übergabe (v1)",
            "## Konsolidierte Empfehlung (BL-30.1 Abschluss)",
            "### Primärkandidat",
            "### Sekundärkandidat",
            "## Angelegte BL-30.2 Follow-ups",
            "## Definition-of-Done-Check (#461)",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in BL-30.1 Closeout-Doku: {marker}")

        for required_term in ["CAND-API-PRO-390", "CAND-BIZ-API-890", "#465", "#466"]:
            self.assertIn(required_term, content, msg=f"Pflichtbegriff fehlt in Closeout-Doku: {required_term}")

    def test_backlog_tracks_bl30_wp4_completion_and_handover(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn(
            "#461 — BL-30.1.wp4 Konsolidierter Abschluss + BL-30.2 Übergabe (abgeschlossen 2026-03-01)",
            backlog,
        )
        self.assertIn("[`docs/BL30_1_CLOSEOUT_V1.md`](BL30_1_CLOSEOUT_V1.md)", backlog)
        self.assertIn("#465/#466", backlog)


if __name__ == "__main__":
    unittest.main()
