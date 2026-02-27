import importlib.util
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
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
        closed = []

        with patch.object(crawler, "list_open_titles", return_value={}):
            with patch.object(crawler, "run_json", return_value=issues):
                with patch.object(crawler, "create_issue", side_effect=lambda *args, **kwargs: created.append((args, kwargs))):
                    with patch.object(crawler, "close_issue", side_effect=lambda *args, **kwargs: closed.append((args, kwargs))):
                        crawler.audit_workstream_balance(dry_run=False)

        self.assertEqual(created, [])
        self.assertEqual(closed, [])

    def test_audit_workstream_balance_closes_existing_issue_when_recovered(self):
        issues = [
            {"title": "Implement API feature", "body": "", "labels": [{"name": "status:blocked"}]},
            {"title": "Docs guide", "body": "", "labels": [{"name": "status:blocked"}]},
            {"title": "Regression test", "body": "", "labels": [{"name": "status:blocked"}]},
        ]
        open_titles = {
            crawler.WORKSTREAM_BALANCE_ISSUE_TITLE: 158,
        }
        closed = []

        with patch.object(crawler, "list_open_titles", return_value=open_titles):
            with patch.object(crawler, "run_json", return_value=issues):
                with patch.object(crawler, "close_issue", side_effect=lambda *args, **kwargs: closed.append((args, kwargs))):
                    crawler.audit_workstream_balance(dry_run=False)

        self.assertEqual(len(closed), 1)
        args, kwargs = closed[0]
        self.assertEqual(args[0], 158)
        self.assertIn("Gap=0 <= Ziel 2", args[1])
        self.assertFalse(kwargs["dry_run"])

    def test_audit_workstream_balance_does_not_create_duplicate_issue(self):
        issues = [
            {"title": "Implement API feature", "body": "", "labels": []},
            {"title": "Service integration", "body": "", "labels": []},
        ]
        open_titles = {
            crawler.WORKSTREAM_BALANCE_ISSUE_TITLE: 98
        }
        created = []

        with patch.object(crawler, "list_open_titles", return_value=open_titles):
            with patch.object(crawler, "run_json", return_value=issues):
                with patch.object(crawler, "create_issue", side_effect=lambda *args, **kwargs: created.append((args, kwargs))):
                    crawler.audit_workstream_balance(dry_run=False)

        self.assertEqual(created, [])

    def test_build_workstream_balance_baseline_computes_gap_and_target(self):
        issues = [
            {"title": "Implement API feature", "body": "", "labels": []},
            {"title": "Build integration", "body": "", "labels": []},
            {"title": "Docs guide", "body": "", "labels": []},
            {"title": "Blocked regression tests", "body": "", "labels": [{"name": "status:blocked"}]},
        ]

        baseline = crawler.build_workstream_balance_baseline(issues)

        self.assertEqual(baseline["counts"]["development"], 2)
        self.assertEqual(baseline["counts"]["documentation"], 1)
        self.assertEqual(baseline["counts"]["testing"], 0)
        self.assertEqual(baseline["gap"], 2)
        self.assertEqual(baseline["target_gap_max"], 2)
        self.assertTrue(baseline["needs_catchup"])

    def test_format_workstream_balance_markdown_contains_core_fields(self):
        baseline = {
            "counts": {"development": 3, "documentation": 2, "testing": 1},
            "gap": 2,
            "target_gap_max": 2,
            "needs_catchup": True,
        }

        rendered = crawler.format_workstream_balance_markdown(baseline, "2026-02-26T21:00:00+00:00")

        self.assertIn("Workstream-Balance Baseline", rendered)
        self.assertIn("Development: **3**", rendered)
        self.assertIn("Dokumentation: **2**", rendered)
        self.assertIn("Testing: **1**", rendered)
        self.assertIn("Ziel-Gap: **<= 2**", rendered)
        self.assertIn("Catch-up nötig: **ja**", rendered)

    def test_print_workstream_balance_report_json_renders_machine_readable_payload(self):
        issues = [
            {"title": "Implement API feature", "body": "", "labels": []},
            {"title": "Docs guide", "body": "", "labels": []},
            {"title": "Regression test", "body": "", "labels": []},
        ]

        with patch.object(crawler, "get_open_issues_for_workstream_balance", return_value=issues):
            with patch.object(crawler, "now_iso", return_value="2026-02-26T21:10:00+00:00"):
                with patch("builtins.print") as mocked_print:
                    crawler.print_workstream_balance_report(report_format="json")

        printed = mocked_print.call_args[0][0]
        payload = json.loads(printed)

        self.assertEqual(payload["generated_at"], "2026-02-26T21:10:00+00:00")
        self.assertEqual(payload["counts"]["development"], 1)
        self.assertEqual(payload["counts"]["documentation"], 1)
        self.assertEqual(payload["counts"]["testing"], 1)
        self.assertFalse(payload["needs_catchup"])


class TestGithubRepoCrawlerTodoFiltering(unittest.TestCase):
    def test_is_actionable_todo_line_filters_done_markers(self):
        self.assertTrue(crawler.is_actionable_todo_line("# TODO: implement parser"))
        self.assertFalse(crawler.is_actionable_todo_line("# TODO ✅ bereits erledigt"))
        self.assertFalse(crawler.is_actionable_todo_line("# FIXME closed via PR #123"))
        self.assertFalse(crawler.is_actionable_todo_line("# TODO changelog note for historical release"))

    def test_scan_repo_for_findings_only_creates_actionable_todo_issues(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir(parents=True, exist_ok=True)
            (root / "src" / "sample.py").write_text(
                "# TODO: implement source mapping\n"
                "# TODO ✅ abgeschlossen nach Merge\n"
                "# FIXME closed in changelog\n",
                encoding="utf-8",
            )

            created_titles = []

            def fake_create_issue(title, body, dry_run, priority="priority:P2"):
                created_titles.append(title)

            with patch.object(crawler, "REPO_ROOT", root):
                with patch.object(crawler, "list_open_titles", return_value={}):
                    with patch.object(crawler, "create_issue", side_effect=fake_create_issue):
                        with patch.object(crawler, "now_iso", return_value="2026-02-27T05:40:00+00:00"):
                            crawler.scan_repo_for_findings(dry_run=False)

            self.assertEqual(len(created_titles), 1)
            self.assertIn("src/sample.py:1", created_titles[0])


if __name__ == "__main__":
    unittest.main()
