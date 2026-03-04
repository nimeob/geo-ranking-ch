import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GUIDE_PATH = REPO_ROOT / "docs" / "api" / "API_DATA_ONLY_UI_MIGRATION_GUIDE.md"


class TestHistoryTraceMigrationRunbookDocs(unittest.TestCase):
    def test_history_trace_before_transition_after_runbook_markers_exist(self):
        content = GUIDE_PATH.read_text(encoding="utf-8")

        required_markers = [
            "### 4.2 Runbook-Flow: History (`before -> transition -> after`)",
            "#### Before (Legacy-Betrieb)",
            "#### Transition (Dual-Readiness)",
            "#### After (UI-only Ownership)",
            "**Rollback-Hinweise (History):**",
            "### 4.3 Runbook-Flow: Trace (`before -> transition -> after`)",
            "**Rollback-Hinweise (Trace):**",
        ]

        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt im History/Trace-Runbook: {marker}")

    def test_history_trace_checks_reference_ui_and_api_paths(self):
        content = GUIDE_PATH.read_text(encoding="utf-8")

        expected_paths = [
            "${UI_BASE_URL}/history",
            "${API_BASE_URL}/analyze/history?limit=5",
            "${UI_BASE_URL}/gui?view=trace&request_id=test",
            "${API_BASE_URL}/debug/trace?request_id=test",
            "${API_BASE_URL}/trace?request_id=test",
        ]

        for path in expected_paths:
            self.assertIn(path, content, msg=f"Verifizierbarer Check fehlt für Pfad: {path}")


if __name__ == "__main__":
    unittest.main()
