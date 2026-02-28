import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_testing_catchup_sequence.sh"
DOC_PATH = REPO_ROOT / "docs" / "testing" / "testing-catchup-regression-smoke-sequence.md"


class TestTestingCatchupSequenceAssets(unittest.TestCase):
    def test_runner_script_exists_and_is_executable(self):
        self.assertTrue(SCRIPT_PATH.is_file(), msg="Catch-up-Runner fehlt")
        self.assertTrue(SCRIPT_PATH.stat().st_mode & 0o111, msg="Runner muss ausführbar sein")

    def test_runner_script_contains_expected_pytest_order(self):
        content = SCRIPT_PATH.read_text(encoding="utf-8")
        expected_sequence = [
            "tests/test_github_repo_crawler.py::TestGithubRepoCrawlerWorkstreamBalance::test_build_workstream_catchup_plan_returns_minimal_delta_per_category",
            "tests/test_github_repo_crawler.py::TestGithubRepoCrawlerWorkstreamBalance::test_print_workstream_balance_report_json_renders_machine_readable_payload",
            "tests/test_bl31_routing_tls_smoke_script.py::TestBl31RoutingTlsSmokeScript::test_smoke_baseline_mode_is_reproducible_with_structured_output",
            "tests/test_bl31_routing_tls_smoke_script.py::TestBl31RoutingTlsSmokeScript::test_strict_mode_matches_cors_baseline_result",
        ]

        positions = []
        for marker in expected_sequence:
            pos = content.find(marker)
            self.assertNotEqual(pos, -1, msg=f"Marker fehlt im Runner: {marker}")
            positions.append(pos)

        self.assertEqual(
            positions,
            sorted(positions),
            msg="pytest-Ziele müssen in der dokumentierten Catch-up-Reihenfolge stehen",
        )

    def test_runbook_defines_prioritization_sequence_and_qa_step(self):
        self.assertTrue(DOC_PATH.is_file(), msg="Catch-up-Runbook fehlt")
        content = DOC_PATH.read_text(encoding="utf-8")

        required_markers = [
            "# Testing Catch-up: Regression + Smoke Priorisierung (Issue #337)",
            "## Priorisierte Szenarien",
            "## Feste pytest-Sequenz (verbindlich)",
            "./scripts/check_testing_catchup_sequence.sh",
            "## QA-Validierungsschritt (Abschlussnachweis)",
            "testing catch-up sequence: PASS",
            "docs/testing/bl31-routing-tls-smoke-catchup.md",
            "docs/BACKLOG.md",
        ]

        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt im Catch-up-Runbook: {marker}")


if __name__ == "__main__":
    unittest.main()
