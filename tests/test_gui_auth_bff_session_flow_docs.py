import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestGuiAuthBffSessionFlowDocs(unittest.TestCase):
    def test_gui_auth_flow_doc_exists_with_required_sections(self):
        doc_path = REPO_ROOT / "docs" / "gui" / "GUI_AUTH_BFF_SESSION_FLOW.md"
        self.assertTrue(doc_path.is_file(), msg="GUI Auth BFF Flow Doku fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# GUI Auth BFF Session Flow",
            "## End-to-End Flow",
            "## Session-Lebenszyklus",
            "## Logout-Flow",
            "## UX-/Redirect-Konvention (Issue #998)",
            "## Failure-Modes (Kurzmatrix)",
            "## Security-Guardrails (verbindlich)",
            "## Reproduzierbarer Dev-E2E-Nachweis (Issue #947)",
            "## Cookie-Security-Evidenz (Issue #947)",
            "## Parent-Acceptance-Referenz (#939 / #978)",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt: {marker}")

        for keyword in ["httpOnly", "SameSite", "Secure", "CSRF"]:
            self.assertIn(keyword, content, msg=f"Security-Keyword fehlt: {keyword}")

        for ux_keyword in ["reason=", "refresh_failed", "consent_denied", "`/login?next="]:
            self.assertIn(ux_keyword, content, msg=f"Auth-Recovery-Keyword fehlt: {ux_keyword}")

        self.assertIn(
            "reports/evidence/issue-947-gui-auth-e2e-cookie-evidence-",
            content,
            msg="Issue-947-Evidence-Link fehlt in der Auth-Flow-Doku",
        )
        self.assertIn(
            "Kurzer E2E-Nachweis in dev dokumentiert",
            content,
            msg="Parent-Acceptance-Referenz auf #939 fehlt",
        )

    def test_cross_links_from_gui_state_flow_and_api_usage(self):
        gui_state_flow = (REPO_ROOT / "docs" / "gui" / "GUI_MVP_STATE_FLOW.md").read_text(
            encoding="utf-8"
        )
        api_usage = (REPO_ROOT / "docs" / "user" / "api-usage.md").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "docs/gui/GUI_AUTH_BFF_SESSION_FLOW.md",
            gui_state_flow,
            msg="GUI State Flow muss auf die GUI Auth BFF Session-Flow-Doku verlinken",
        )
        self.assertIn(
            "docs/gui/GUI_AUTH_BFF_SESSION_FLOW.md",
            api_usage,
            msg="User API Usage muss auf die GUI Auth BFF Session-Flow-Doku verlinken",
        )

    def test_auth_mvp_ac_matrix_doc_exists_with_expected_references(self):
        matrix_path = REPO_ROOT / "docs" / "gui" / "GUI_AUTH_MVP_AC_MATRIX_978.md"
        self.assertTrue(matrix_path.is_file(), msg="GUI Auth MVP AC Matrix Doku fehlt")

        content = matrix_path.read_text(encoding="utf-8")
        required_markers = [
            "# GUI Auth MVP — Acceptance-Matrix für Issue #978",
            "## AC-Matrix",
            "GUI ohne manuelles Bearer-Token nutzbar",
            "Login/Callback/Logout End-to-End in dev verifiziert",
            "Session-Cookie korrekt gesetzt",
            "## Gap-Bewertung",
            "keine neuen funktionalen Gaps",
            "issue-995-auth-ac-matrix-20260303T185411Z.md",
            "issue-998-auth-ux-runbook-sync-20260303T1949Z.md",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in AC-Matrix: {marker}")

        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            "docs/gui/GUI_AUTH_MVP_AC_MATRIX_978.md",
            readme,
            msg="README muss auf die GUI Auth MVP AC Matrix verlinken",
        )


if __name__ == "__main__":
    unittest.main()
