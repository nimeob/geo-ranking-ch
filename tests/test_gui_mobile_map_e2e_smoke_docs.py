from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestGuiMobileMapE2ESmokeDocs(unittest.TestCase):
    def test_mobile_smoke_doc_contains_required_markers(self) -> None:
        doc_path = REPO_ROOT / "docs" / "testing" / "GUI_MOBILE_MAP_E2E_SMOKE.md"
        self.assertTrue(doc_path.is_file(), msg="GUI_MOBILE_MAP_E2E_SMOKE.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "#981",
            "#975",
            "iOS Safari Simulator",
            "Android Chrome Simulator",
            "Pinch-Zoom",
            "Pan/Marker-Regression",
            "Geolocation Erfolg",
            "Geolocation Fehlerfall",
            "issue-981-mobile-e2e-smoke-20260303T181805Z.json",
            "scripts/run_issue_981_mobile_smoke.mjs",
        ]
        for marker in required_markers:
            self.assertIn(marker, content)

    def test_smoke_script_exists(self) -> None:
        script_path = REPO_ROOT / "scripts" / "run_issue_981_mobile_smoke.mjs"
        self.assertTrue(script_path.is_file(), msg="run_issue_981_mobile_smoke.mjs fehlt")


if __name__ == "__main__":
    unittest.main()
