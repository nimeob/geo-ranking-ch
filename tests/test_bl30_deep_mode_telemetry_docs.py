import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30DeepModeTelemetryDocs(unittest.TestCase):
    def test_logging_schema_mentions_deep_mode_events_and_evidence(self):
        content = (REPO_ROOT / "docs" / "LOGGING_SCHEMA_V1.md").read_text(encoding="utf-8")

        required_markers = [
            "api.deep_mode.gate_evaluated",
            "api.deep_mode.execution.start",
            "api.deep_mode.execution.retry",
            "api.deep_mode.execution.abort",
            "api.deep_mode.execution.end",
            "tests/test_bl30_deep_mode_telemetry_events.py",
            "docs/testing/DEEP_MODE_TRACE_EVIDENCE_RUNBOOK.md",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt im Logging-Schema: {marker}")

    def test_runbook_and_sample_artifact_exist_with_required_markers(self):
        runbook_path = REPO_ROOT / "docs" / "testing" / "DEEP_MODE_TRACE_EVIDENCE_RUNBOOK.md"
        self.assertTrue(runbook_path.is_file(), msg="Runbook für Deep-Mode Trace-Evidence fehlt")

        runbook_content = runbook_path.read_text(encoding="utf-8")
        self.assertIn("api.deep_mode.gate_evaluated", runbook_content)
        self.assertIn("api.deep_mode.execution.end", runbook_content)
        self.assertIn("api.deep_mode.execution.abort", runbook_content)

        sample_path = REPO_ROOT / "docs" / "testing" / "deep-mode-trace-evidence-sample.jsonl"
        self.assertTrue(sample_path.is_file(), msg="Deep-Mode-Trace-Beispielartefakt fehlt")

        sample_lines = [line for line in sample_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertGreaterEqual(len(sample_lines), 5, msg="Beispielartefakt enthält zu wenige Events")

    def test_backlog_tracks_wp2_r2_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn(
            "#473 — BL-30.3.wp2.r2 Deep-Mode-Telemetrie + Trace-Evidence absichern (abgeschlossen 2026-03-01)",
            backlog,
        )
        self.assertIn("tests/test_bl30_deep_mode_telemetry_events.py", backlog)
        self.assertIn("docs/testing/DEEP_MODE_TRACE_EVIDENCE_RUNBOOK.md", backlog)


if __name__ == "__main__":
    unittest.main()
