import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestGTMToDBArchitectureV1Docs(unittest.TestCase):
    def test_gtm_to_db_architecture_doc_contains_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "GTM_TO_DB_ARCHITECTURE_V1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/GTM_TO_DB_ARCHITECTURE_V1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# GTM → Data Architecture Mapping v1",
            "## GTM → technische Konsequenzen (v1)",
            "## Kanonisches Kern-Datenmodell v1",
            "## Tenant-Grenzen & Ownership-Regeln (verbindlich v1)",
            "## No-regrets Defaults (für Umsetzung)",
            "## Trade-offs / offene Fragen",
            "Issue: #585 (Parent #577)",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Pflichtmarker fehlt: {marker}")

        for token in [
            "organizations",
            "memberships",
            "subscriptions",
            "entitlements",
            "usage_counters",
            "api_keys",
            "audit_events",
        ]:
            self.assertIn(token, content, msg=f"Kern-Entity fehlt: {token}")

    def test_backlog_tracks_issue_585_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("#585 abgeschlossen", backlog)
        self.assertIn("[`docs/GTM_TO_DB_ARCHITECTURE_V1.md`](GTM_TO_DB_ARCHITECTURE_V1.md)", backlog)
        self.assertIn("#577 atomisiert in Work-Packages #585/#586/#587/#588", backlog)


if __name__ == "__main__":
    unittest.main()
