from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestGuiDevLiveAuthAnalyzeSmokeDocs(unittest.TestCase):
    def test_doc_contains_required_markers(self) -> None:
        doc_path = REPO_ROOT / "docs" / "testing" / "GUI_DEV_LIVE_AUTH_ANALYZE_SMOKE.md"
        self.assertTrue(doc_path.is_file(), msg="GUI_DEV_LIVE_AUTH_ANALYZE_SMOKE.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "scripts/run_dev_ui_auth_analyze_smoke.mjs",
            "scripts/smoke/validate_gui_live_auth_analyze_secrets.sh",
            "scripts/smoke/ch_live_addresses.txt",
            "gui-dev-live-auth-analyze-smoke.yml",
            "DEV_UI_SMOKE_USERNAME",
            "DEV_UI_SMOKE_PASSWORD",
            "POST /analyze",
            "session_expired",
            "401",
            "gui-dev-live-auth-analyze-smoke-artifacts",
            "dev-ui-auth-analyze-smoke-",
            "dev-ui-auth-analyze-smoke-blocked-",
        ]
        for marker in required_markers:
            self.assertIn(marker, content)

    def test_script_workflow_and_address_pool_exist(self) -> None:
        script_path = REPO_ROOT / "scripts" / "run_dev_ui_auth_analyze_smoke.mjs"
        workflow_path = REPO_ROOT / ".github" / "workflows" / "gui-dev-live-auth-analyze-smoke.yml"
        address_pool_path = REPO_ROOT / "scripts" / "smoke" / "ch_live_addresses.txt"

        self.assertTrue(script_path.is_file(), msg="run_dev_ui_auth_analyze_smoke.mjs fehlt")
        self.assertTrue(workflow_path.is_file(), msg="gui-dev-live-auth-analyze-smoke.yml fehlt")
        self.assertTrue(address_pool_path.is_file(), msg="ch_live_addresses.txt fehlt")


if __name__ == "__main__":
    unittest.main()
