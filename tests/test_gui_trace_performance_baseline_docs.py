import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestGuiTracePerformanceBaselineDocs(unittest.TestCase):
    def test_trace_performance_baseline_section_is_present_and_complete(self):
        doc_path = REPO_ROOT / "docs" / "gui" / "GUI_MVP_STATE_FLOW.md"
        self.assertTrue(doc_path.is_file(), msg="GUI_MVP_STATE_FLOW.md fehlt")

        content = doc_path.read_text(encoding="utf-8")

        required_markers = [
            "### Trace-Performance-Baseline (Dev)",
            "`ui.trace.request.end`",
            "`duration_ms`",
            "`timeline_state`",
            "`timeline_events`",
            "`P95 <= 1200 ms`",
            "`P95 > 1200 ms`",
            "`P95 > 2500 ms`",
            "`< 2%`",
            "`>= 2%`",
            "`>= 5%`",
        ]

        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Trace-Performance-Baseline-Marker fehlt: {marker}")


if __name__ == "__main__":
    unittest.main()
