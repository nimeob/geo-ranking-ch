from pathlib import Path
import json
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestDevDashboardDocs(unittest.TestCase):
    def test_dashboard_doc_covers_queries_windows_and_thresholds(self) -> None:
        doc_path = REPO_ROOT / "docs" / "observability" / "DEV_DASHBOARD.md"
        self.assertTrue(doc_path.is_file(), msg="DEV_DASHBOARD.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "IF(mt>=20,(m5/mt)*100,0)",
            "TargetResponseTime",
            "p95",
            "15m",
            "1h",
            "Warnung ab `>= 2%`",
            "Kritisch ab `>= 5%`",
            "Warnung ab `>= 1.2s`",
            "Kritisch ab `>= 2.5s`",
            "docs/observability/dev-dashboard-cloudwatch.json",
        ]
        for marker in required_markers:
            self.assertIn(marker, content)

    def test_dashboard_export_has_exactly_two_metric_widgets(self) -> None:
        export_path = REPO_ROOT / "docs" / "observability" / "dev-dashboard-cloudwatch.json"
        self.assertTrue(export_path.is_file(), msg="Dashboard-Export fehlt")

        data = json.loads(export_path.read_text(encoding="utf-8"))
        widgets = data.get("widgets", [])
        metric_widgets = [w for w in widgets if w.get("type") == "metric"]
        self.assertEqual(
            len(metric_widgets),
            2,
            msg="Dashboard muss genau zwei Kernmetriken (5xx + p95) enthalten",
        )


if __name__ == "__main__":
    unittest.main()
