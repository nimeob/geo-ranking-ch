import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
CRAWLER_PATH = REPO_ROOT / "scripts" / "github_repo_crawler.py"

spec = importlib.util.spec_from_file_location("github_repo_crawler", CRAWLER_PATH)
crawler = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(crawler)


class TestGithubRepoCrawlerWorkstreamBalance(unittest.TestCase):
    def test_compute_workstream_counts_ignores_blocked_and_crawler_auto(self):
        issues = [
            {
                "title": "Implement API feature",
                "body": "",
                "labels": [],
            },
            {
                "title": "Testing regression suite",
                "body": "",
                "labels": [],
            },
            {
                "title": "Docs runbook update",
                "body": "",
                "labels": [{"name": "status:blocked"}],
            },
            {
                "title": "Crawler generated ticket",
                "body": "test",
                "labels": [{"name": "crawler:auto"}],
            },
        ]

        counts = crawler.compute_workstream_counts(issues)

        self.assertEqual(
            counts,
            {
                "development": 1,
                "documentation": 0,
                "testing": 1,
            },
        )

    def test_keyword_matching_avoids_gui_false_positive_in_guide(self):
        issues = [
            {"title": "Documentation guide for operators", "body": "", "labels": []},
        ]

        counts = crawler.compute_workstream_counts(issues)

        self.assertEqual(counts["development"], 0)
        self.assertEqual(counts["documentation"], 1)

    def test_audit_workstream_balance_creates_p0_issue_when_gap_is_too_large(self):
        issues = [
            {"title": "Implement API feature", "body": "", "labels": []},
            {"title": "Service integration", "body": "", "labels": []},
            {"title": "Docs architecture guide", "body": "", "labels": []},
        ]
        created = []

        def fake_create_issue(title, body, dry_run, priority="priority:P2"):
            created.append({"title": title, "body": body, "dry_run": dry_run, "priority": priority})

        with patch.object(crawler, "list_open_titles", return_value={}):
            with patch.object(crawler, "run_json", return_value=issues):
                with patch.object(crawler, "create_issue", side_effect=fake_create_issue):
                    with patch.object(crawler, "now_iso", return_value="2026-02-26T20:42:40+00:00"):
                        crawler.audit_workstream_balance(dry_run=False)

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]["priority"], "priority:P0")
        self.assertIn("Development: **2**", created[0]["body"])
        self.assertIn("Dokumentation: **1**", created[0]["body"])
        self.assertIn("Testing: **0**", created[0]["body"])

    def test_audit_workstream_balance_skips_when_balanced(self):
        issues = [
            {"title": "Implement API feature", "body": "", "labels": []},
            {"title": "Docs guide", "body": "", "labels": []},
            {"title": "Regression test", "body": "", "labels": []},
        ]
        created = []

        with patch.object(crawler, "list_open_titles", return_value={}):
            with patch.object(crawler, "run_json", return_value=issues):
                with patch.object(crawler, "create_issue", side_effect=lambda *args, **kwargs: created.append((args, kwargs))):
                    crawler.audit_workstream_balance(dry_run=False)

        self.assertEqual(created, [])

    def test_audit_workstream_balance_does_not_create_duplicate_issue(self):
        issues = [
            {"title": "Implement API feature", "body": "", "labels": []},
            {"title": "Service integration", "body": "", "labels": []},
        ]
        open_titles = {
            "[Crawler][P0] Workstream-Balance: Development/Dokumentation/Testing angleichen": 98
        }
        created = []

        with patch.object(crawler, "list_open_titles", return_value=open_titles):
            with patch.object(crawler, "run_json", return_value=issues):
                with patch.object(crawler, "create_issue", side_effect=lambda *args, **kwargs: created.append((args, kwargs))):
                    crawler.audit_workstream_balance(dry_run=False)

        self.assertEqual(created, [])


if __name__ == "__main__":
    unittest.main()
