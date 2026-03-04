from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestGuiWebkitSmokeDocs(unittest.TestCase):
    def test_doc_contains_required_markers(self) -> None:
        doc_path = REPO_ROOT / "docs" / "testing" / "GUI_WEBKIT_SMOKE.md"
        self.assertTrue(doc_path.is_file(), msg="GUI_WEBKIT_SMOKE.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "#986",
            "#975",
            "#981",
            "playwright install --with-deps webkit",
            "scripts/run_issue_986_webkit_smoke.mjs",
            "gui-webkit-smoke.yml",
            "gui-webkit-smoke-artifacts",
            "issue-986-webkit-smoke-",
        ]
        for marker in required_markers:
            self.assertIn(marker, content)

    def test_smoke_script_and_workflow_exist(self) -> None:
        script_path = REPO_ROOT / "scripts" / "run_issue_986_webkit_smoke.mjs"
        workflow_path = REPO_ROOT / ".github" / "workflows" / "gui-webkit-smoke.yml"
        self.assertTrue(script_path.is_file(), msg="run_issue_986_webkit_smoke.mjs fehlt")
        self.assertTrue(workflow_path.is_file(), msg="gui-webkit-smoke.yml fehlt")


if __name__ == "__main__":
    unittest.main()
