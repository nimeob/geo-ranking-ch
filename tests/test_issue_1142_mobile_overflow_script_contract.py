from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestIssue1142MobileOverflowScriptContract(unittest.TestCase):
    def test_script_enforces_after_assertions_and_exit_code(self) -> None:
        script_path = REPO_ROOT / "scripts" / "run_issue_1142_mobile_table_overflow_smoke.cjs"
        self.assertTrue(script_path.is_file(), msg="Issue-1142-Smoke-Skript fehlt")

        content = script_path.read_text(encoding="utf-8")
        required_markers = [
            "ISSUE_1142_BASELINE_REF",
            "ISSUE_1142_BASE_URL",
            "ISSUE_1142_REMOTE_TIMEOUT_MS",
            "const repoRoot = path.resolve(__dirname, '..');",
            "normalizeGuiBaseUrl",
            "fetchGuiHtmlFromBaseUrl",
            "targetUrlRequested",
            "currentHtmlSource",
            "currentHtmlFetchError",
            "baselineRefRequested",
            "baselineRefResolved",
            "baselineFallbackUsed",
            "baselineEqualsCurrent",
            "assertions",
            "afterDocNoOverflow",
            "afterShellNoOverflow",
            "afterTableNoOverflow",
            "afterActionsVisible",
            "if (!payload.ok)",
            "process.exit(1);",
        ]

        for marker in required_markers:
            self.assertIn(marker, content)


if __name__ == "__main__":
    unittest.main()
