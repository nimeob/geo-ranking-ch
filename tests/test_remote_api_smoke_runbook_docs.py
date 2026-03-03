from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestRemoteApiSmokeRunbookDocs(unittest.TestCase):
    def test_runbook_covers_auth_preflight_contract_and_troubleshooting(self) -> None:
        doc_path = REPO_ROOT / "docs" / "testing" / "REMOTE_API_SMOKE_RUNBOOK.md"
        self.assertTrue(doc_path.is_file(), msg="REMOTE_API_SMOKE_RUNBOOK.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "scripts/run_deploy_smoke.py",
            "scripts/smoke/auth_preflight.sh",
            ".github/workflows/deploy.yml",
            "SMOKE_AUTH_MODE",
            "OIDC_TOKEN_URL",
            "OIDC_CLIENT_ID",
            "OIDC_CLIENT_SECRET",
            "OIDC_CLIENT_SECRET_FILE",
            "SMOKE_BEARER_TOKEN",
            "auth-preflight-failed",
            "blocked-by-auth",
            "Lokale Verifikation",
            "Troubleshooting",
        ]
        for marker in required_markers:
            self.assertIn(marker, content)


if __name__ == "__main__":
    unittest.main()
