from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestGuiAuthSmokeRunbookDocs(unittest.TestCase):
    def test_runbook_mentions_issue_1019_smoke_and_entrypoint(self) -> None:
        doc_path = REPO_ROOT / "docs" / "testing" / "GUI_AUTH_SMOKE_RUNBOOK.md"
        self.assertTrue(doc_path.is_file(), msg="GUI_AUTH_SMOKE_RUNBOOK.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "#1019",
            "tests/test_auth_regression_smoke_issue_1019.py",
            "scripts/run_webservice_e2e.sh",
            "login -> analyze/history -> logout",
            "login -> protected route -> logout -> relogin",
            "kein API-Host im browser-sichtbaren Auth-Flow",
            "invalid_state",
            "consent_denied",
            "session_expired",
        ]
        for marker in required_markers:
            self.assertIn(marker, content)


if __name__ == "__main__":
    unittest.main()
