import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestDevStageCutoverRunbookDocs(unittest.TestCase):
    def test_canonical_cutover_runbook_contains_required_gate_structure(self):
        doc = REPO_ROOT / "docs" / "testing" / "DEV_STAGE_CUTOVER_RUNBOOK.md"
        self.assertTrue(doc.is_file(), msg="DEV_STAGE_CUTOVER_RUNBOOK.md fehlt")

        content = doc.read_text(encoding="utf-8")

        required_markers = [
            "# Dev→Stage Cutover Runbook (kanonisch)",
            "### Gate 1 — Auth-Smoke (UI-Login + Session-Check 200)",
            "### Gate 2 — Kritischer UI-Happy-Path vollständig durchlaufbar",
            "### Gate 3 — Dev-Error-Rate über 10 Minuten < 1%",
            "## 4) Linearer Cutover-Ablauf (Stop/Go)",
            "Entscheidung <= 10 Min",
            "## 5) Rollback (harte Trigger + Minimalpfad)",
            "Trigger erkannt",
            "Auth-Smoke Re-Check",
            "## 6) Post-Cutover-Checks (Minute 5/10/15)",
            "+5 min",
            "+10 min",
            "+15 min",
            "## 7) Kompaktes Dry-Run-Protokoll (Dev)",
        ]
        for marker in required_markers:
            self.assertIn(marker, content)

        # 3 verbindliche Primary-Verify-Kommandos (ein Gate = ein Primary)
        self.assertEqual(content.count("**Primary Verify**"), 3)

    def test_testing_index_links_to_canonical_cutover_runbook(self):
        index_content = (REPO_ROOT / "docs" / "testing" / "RUNBOOKS.md").read_text(encoding="utf-8")
        self.assertIn("DEV_STAGE_CUTOVER_RUNBOOK.md", index_content)


if __name__ == "__main__":
    unittest.main()
