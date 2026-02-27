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


class TestGithubRepoCrawlerVisionIssueCoverage(unittest.TestCase):
    def test_parse_vision_requirements_extracts_scope_modules(self):
        markdown = """
# Vision
## Scope-Module (fachlich)
### M1 — Gebäudeprofil
- Adress-Geocoding
- Energieträger

### M2 — Umfeldprofil
- ÖV-Erreichbarkeit

## Andere Sektion
### M3 — ignorieren
- sollte nicht mehr mitlaufen
""".strip()

        requirements = crawler.parse_vision_requirements(markdown)

        self.assertEqual([item["id"] for item in requirements], ["M1", "M2"])
        self.assertEqual(requirements[0]["title"], "Gebäudeprofil")
        self.assertIn("adress", " ".join(requirements[0]["tokens"]))

    def test_assess_vision_issue_coverage_marks_covered_unclear_missing(self):
        requirements = [
            {"id": "M1", "title": "Gebäudeprofil", "line": 10, "tokens": ["gebäude", "baujahr"]},
            {"id": "M2", "title": "Umfeldprofil", "line": 14, "tokens": ["umfeld", "lärm"]},
            {"id": "M3", "title": "Bau-Eignung", "line": 20, "tokens": ["hangneigung", "zugänglichkeit"]},
        ]
        issues = [
            {"number": 21, "title": "Gebäude Baujahr ergänzen", "body": "Gebäudeprofil ausbauen", "state": "open", "url": "https://example/21"},
            {"number": 22, "title": "Lärmindikatoren dokumentieren", "body": "", "state": "closed", "url": "https://example/22"},
        ]

        coverage = crawler.assess_vision_issue_coverage(requirements, issues)

        self.assertEqual(coverage["total_requirements"], 3)
        self.assertEqual(coverage["covered"], 1)
        self.assertEqual(coverage["unclear"], 1)
        self.assertEqual(coverage["missing"], 1)
        status_by_id = {row["id"]: row["status"] for row in coverage["requirements"]}
        self.assertEqual(status_by_id["M1"], "covered")
        self.assertEqual(status_by_id["M2"], "unclear")
        self.assertEqual(status_by_id["M3"], "missing")

    def test_collect_vision_issue_coverage_findings_creates_gap_and_unclear(self):
        coverage = {
            "requirements": [
                {
                    "id": "M1",
                    "title": "Gebäudeprofil",
                    "line": 33,
                    "status": "missing",
                    "best_match": None,
                },
                {
                    "id": "M2",
                    "title": "Umfeldprofil",
                    "line": 40,
                    "status": "unclear",
                    "best_match": {"number": 55, "url": "https://example/55"},
                },
            ]
        }

        findings = crawler.collect_vision_issue_coverage_findings(coverage)

        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]["type"], "vision_issue_coverage_gap")
        self.assertEqual(findings[1]["type"], "vision_issue_coverage_unclear")


class TestGithubRepoCrawlerConsistencyReport(unittest.TestCase):
    def test_build_consistency_report_prioritizes_by_severity(self):
        findings = [
            crawler.build_finding(
                finding_type="todo_actionable",
                severity="low",
                summary="Low severity finding",
                evidence=[{"kind": "file_line", "path": "src/a.py", "line": 1}],
                source={"kind": "repository_scan", "component": "todo_fixme"},
            ),
            crawler.build_finding(
                finding_type="issue_closure_consistency",
                severity="critical",
                summary="Critical closure inconsistency",
                evidence=[{"kind": "issue", "number": 123}],
                source={"kind": "github_issue_audit", "component": "closed_issue_review"},
            ),
        ]

        report = crawler.build_consistency_report(findings, generated_at="2026-02-27T06:00:00+00:00")

        self.assertEqual(report["schema_version"], "1.0")
        self.assertEqual(report["summary"]["total_findings"], 2)
        self.assertEqual(report["summary"]["by_severity"]["critical"], 1)
        self.assertEqual(report["summary"]["by_severity"]["low"], 1)
        self.assertEqual(report["findings"][0]["severity"], "critical")
        self.assertEqual(report["findings"][0]["type"], "issue_closure_consistency")

    def test_render_consistency_report_markdown_includes_coverage_block(self):
        report = crawler.build_consistency_report(
            [],
            generated_at="2026-02-27T06:08:00+00:00",
            coverage={
                "vision_source": "docs/VISION_PRODUCT.md",
                "total_requirements": 2,
                "covered": 1,
                "unclear": 1,
                "missing": 0,
                "requirements": [
                    {
                        "id": "M1",
                        "title": "Gebäudeprofil",
                        "status": "covered",
                        "matched_keywords": ["gebäude", "baujahr"],
                        "best_match": {"number": 21, "state": "open", "score": 2},
                    },
                    {
                        "id": "M2",
                        "title": "Umfeldprofil",
                        "status": "unclear",
                        "matched_keywords": ["lärm"],
                        "best_match": {"number": 22, "state": "closed", "score": 1},
                    },
                ],
            },
        )

        markdown = crawler.render_consistency_report_markdown(report)

        self.assertIn("Vision ↔ Issue Coverage (MVP)", markdown)
        self.assertIn("Anforderungen: **2**", markdown)
        self.assertIn("M2 — Umfeldprofil", markdown)
        self.assertIn("#22 (closed, score=1)", markdown)

    def test_write_consistency_reports_writes_json_and_markdown(self):
        report = crawler.build_consistency_report(
            [
                crawler.build_finding(
                    finding_type="workstream_balance_gap",
                    severity="medium",
                    summary="Gap > Zielwert",
                    evidence=[{"kind": "metric", "name": "gap", "value": 3}],
                    source={"kind": "workstream_balance", "component": "heuristic_counts"},
                )
            ],
            generated_at="2026-02-27T06:05:00+00:00",
        )

        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with patch.object(crawler, "REPO_ROOT", root):
                json_path, md_path = crawler.write_consistency_reports(
                    report,
                    json_path=Path("reports/consistency_report.json"),
                    markdown_path=Path("reports/consistency_report.md"),
                )

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            markdown = md_path.read_text(encoding="utf-8")

        self.assertEqual(payload["schema_version"], "1.0")
        self.assertEqual(payload["findings"][0]["type"], "workstream_balance_gap")
        self.assertIn("Priorisierte Zusammenfassung", markdown)
        self.assertIn("workstream_balance_gap", markdown)


class TestGithubRepoCrawlerTodoFiltering(unittest.TestCase):
    def test_is_actionable_todo_line_filters_done_markers(self):
        self.assertTrue(crawler.is_actionable_todo_line("# TODO: implement parser"))  # crawler:ignore
        self.assertFalse(crawler.is_actionable_todo_line("# TODO ✅ bereits erledigt"))  # crawler:ignore
        self.assertFalse(crawler.is_actionable_todo_line("# FIXME closed via PR #123"))  # crawler:ignore
        self.assertFalse(crawler.is_actionable_todo_line("# TODO changelog note for historical release"))  # crawler:ignore

    def test_scan_repo_for_findings_only_creates_actionable_todo_issues(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir(parents=True, exist_ok=True)
            (root / "src" / "sample.py").write_text(
                "# TODO: implement source mapping\n"  # crawler:ignore
                "# TODO ✅ abgeschlossen nach Merge\n"  # crawler:ignore
                "# FIXME closed in changelog\n",  # crawler:ignore
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
