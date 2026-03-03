from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestGuiMobileOverflowSmokeDocs(unittest.TestCase):
    def test_mobile_overflow_doc_contains_required_markers(self) -> None:
        doc_path = REPO_ROOT / "docs" / "testing" / "GUI_MOBILE_OVERFLOW_SMOKE.md"
        self.assertTrue(doc_path.is_file(), msg="GUI_MOBILE_OVERFLOW_SMOKE.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "Issue #1039",
            "360x800",
            "document.scrollingElement.scrollWidth === document.scrollingElement.clientWidth",
            "scripts/run_issue_1039_mobile_overflow_smoke.cjs",
            "issue-1039-mobile-overflow-smoke-",
            "issue-1039-mobile-overflow-",
            "issue-1039-desktop-regression-",
            "Desktop-Regressionscheck",
        ]
        for marker in required_markers:
            self.assertIn(marker, content)

    def test_smoke_script_exists(self) -> None:
        script_path = REPO_ROOT / "scripts" / "run_issue_1039_mobile_overflow_smoke.cjs"
        self.assertTrue(script_path.is_file(), msg="run_issue_1039_mobile_overflow_smoke.cjs fehlt")


if __name__ == "__main__":
    unittest.main()
