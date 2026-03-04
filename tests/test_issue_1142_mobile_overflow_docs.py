from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestIssue1142MobileOverflowDocs(unittest.TestCase):
    def test_doc_contains_core_markers(self) -> None:
        doc_path = REPO_ROOT / "docs" / "testing" / "GUI_RESULTS_TABLE_MOBILE_OVERFLOW_ISSUE_1142.md"
        self.assertTrue(doc_path.is_file(), msg="Issue-1142-Doku fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "Issue #1142",
            "@media (max-width: 390px)",
            "issue-1142-mobile-before.png",
            "issue-1142-mobile-after.png",
            "issue-1142-mobile-overflow-evidence.json",
            "scripts/run_issue_1142_mobile_table_overflow_smoke.cjs",
        ]
        for marker in required_markers:
            self.assertIn(marker, content)

    def test_smoke_script_exists(self) -> None:
        script_path = REPO_ROOT / "scripts" / "run_issue_1142_mobile_table_overflow_smoke.cjs"
        self.assertTrue(script_path.is_file(), msg="Issue-1142-Smoke-Skript fehlt")


if __name__ == "__main__":
    unittest.main()
