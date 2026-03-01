import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30UiPerformanceBudgetDocs(unittest.TestCase):
    def test_performance_budget_doc_exists_with_core_sections(self):
        doc_path = REPO_ROOT / "docs" / "gui" / "HTML5_UI_PERFORMANCE_BUDGET_CACHING_V1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/gui/HTML5_UI_PERFORMANCE_BUDGET_CACHING_V1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-30.4.wp3 — Performance-Budget + Browser-Caching-Strategie v1",
            "## 1) Performance-Budget v1 (LCP/TTI/Input-Latency/Request-Limits)",
            "## 2) Messmethode + Telemetrie-Mindeststandard",
            "## 3) Browser-Caching-Strategie nach Datenklasse",
            "## 4) Invalidation-/Revalidation-Regeln",
            "## 5) Auswertungsablauf (Perf-/UX-Diagnostik)",
            "## 7) Definition-of-Done-Check (#481)",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in BL-30.4.wp3 Doku: {marker}")

        for required_term in [
            "LCP",
            "TTI",
            "Input-Latency",
            "Cache-Control",
            "ETag",
            "stale-while-revalidate",
            "PerformanceObserver",
            "ui.state.transition",
            "ui.api.request.start",
            "ui.api.request.end",
            "X-Request-Id",
            "X-Session-Id",
            "#482",
        ]:
            self.assertIn(required_term, content, msg=f"Pflichtbegriff fehlt in BL-30.4.wp3 Doku: {required_term}")

    def test_backlog_tracks_bl30_4_wp3_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn(
            "#481 — BL-30.4.wp3 Performance-Budget + Browser-Caching-Strategie v1 (abgeschlossen 2026-03-01)",
            backlog,
        )
        self.assertIn(
            "[`docs/gui/HTML5_UI_PERFORMANCE_BUDGET_CACHING_V1.md`](gui/HTML5_UI_PERFORMANCE_BUDGET_CACHING_V1.md)",
            backlog,
        )
        self.assertIn("tests/test_bl30_ui_performance_budget_docs.py", backlog)


if __name__ == "__main__":
    unittest.main()
