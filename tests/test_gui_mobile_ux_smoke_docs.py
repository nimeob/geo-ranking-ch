from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestGuiMobileUxSmokeDocs(unittest.TestCase):
    def test_mobile_ux_doc_contains_required_markers(self) -> None:
        doc_path = REPO_ROOT / "docs" / "testing" / "GUI_MOBILE_UX_SMOKE.md"
        self.assertTrue(doc_path.is_file(), msg="GUI_MOBILE_UX_SMOKE.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "#1016",
            "#1015",
            "Burger-Menü UX",
            "Pinch-Zoom Smoothness",
            "scripts/run_issue_1016_mobile_ux_smoke.mjs",
            "issue-1016-mobile-ux-smoke-",
            "issue-1016-mobile-ux-",
        ]
        for marker in required_markers:
            self.assertIn(marker, content)

    def test_smoke_script_exists(self) -> None:
        script_path = REPO_ROOT / "scripts" / "run_issue_1016_mobile_ux_smoke.mjs"
        self.assertTrue(script_path.is_file(), msg="run_issue_1016_mobile_ux_smoke.mjs fehlt")


if __name__ == "__main__":
    unittest.main()
