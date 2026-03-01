import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestComplianceExternalDirectAccessControlDocs(unittest.TestCase):
    def test_external_direct_access_control_doc_exists_with_required_markers(self):
        doc_path = (
            REPO_ROOT
            / "docs"
            / "compliance"
            / "EXTERNAL_DIRECT_ACCESS_CONTROL_V1.md"
        )
        self.assertTrue(
            doc_path.is_file(),
            msg="docs/compliance/EXTERNAL_DIRECT_ACCESS_CONTROL_V1.md fehlt",
        )

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# Minimum-Compliance-Set — Externer Direktzugriff / Login-Sperre v1",
            "## Verbindliche Runtime-Regel",
            "external_direct_login_disabled",
            "api.auth.direct_login.blocked",
            "## Konfigurationstest (Akzeptanzkriterium)",
            "curl -sS -i http://127.0.0.1:8080/login",
            "Issue #524",
        ]
        for marker in required_markers:
            self.assertIn(
                marker,
                content,
                msg=f"Marker fehlt in Externer-Direktzugriff-Doku: {marker}",
            )

    def test_backlog_tracks_issue_524_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("### BL-342 — Minimum-Compliance-Set (Governance-Rollout)", backlog)
        self.assertIn(
            "#524 — Externen Direktzugriff technisch unterbinden (abgeschlossen 2026-03-01)",
            backlog,
        )


if __name__ == "__main__":
    unittest.main()
