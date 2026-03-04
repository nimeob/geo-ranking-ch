from pathlib import Path
import re
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestApiUiDevSmokeMatrixDocs(unittest.TestCase):
    def test_matrix_contains_exactly_six_required_cases(self) -> None:
        doc_path = REPO_ROOT / "docs" / "testing" / "API_UI_DEV_SMOKE_MATRIX_V1.md"
        self.assertTrue(doc_path.is_file(), msg="API_UI_DEV_SMOKE_MATRIX_V1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        row_numbers = re.findall(r"^\|\s*([1-6])\s*\|", content, flags=re.MULTILINE)
        self.assertEqual(
            row_numbers,
            ["1", "2", "3", "4", "5", "6"],
            msg="Die Matrix muss genau die sechs Pflichtfälle 1..6 enthalten.",
        )

        required_markers = [
            "UI Login erfolgreich",
            "Geschützte Route ohne Session",
            "History Happy Path im UI",
            "Trace Happy Path im UI",
            "API-Deprecation-Signal für Legacy-Auth/History/Trace",
            "Negativer API-Contract-Fall (fehlender/ungültiger Parameter)",
            "## Dev-Smoke-Gate (minimal, verbindlich)",
            "tests/test_auth_regression_smoke_issue_1019.py",
            "test_no_api_host_in_browser_auth_flow_guard",
            "leakt keinen API-Host in browser-sichtbaren Auth-Redirects", 
            "tests/test_web_service_bff_gui_guard.py",
            "tests/test_history_navigation_integration.py",
            "tests/test_trace_debug_smoke.py",
            "test_trace_deep_link_state_flow_markers_present",
            "tests/test_history_api_deprecation.py",
            "tests/test_trace_legacy_deprecation.py::test_trace_legacy_alias_returns_gone_with_deprecation_headers",
            "tests/test_api_contract_v1.py",
            "#1211",
        ]
        for marker in required_markers:
            self.assertIn(marker, content)

    def test_deploy_test_tiers_links_matrix(self) -> None:
        tiers_path = REPO_ROOT / "docs" / "testing" / "DEPLOY_TEST_TIERS.md"
        content = tiers_path.read_text(encoding="utf-8")
        self.assertIn("API_UI_DEV_SMOKE_MATRIX_V1.md", content)
        self.assertIn("genau 6 Pflichtfälle", content)


if __name__ == "__main__":
    unittest.main()
