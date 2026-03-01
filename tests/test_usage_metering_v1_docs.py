import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestUsageMeteringV1Docs(unittest.TestCase):
    def test_usage_metering_doc_exists_with_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "USAGE_METERING_v1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/USAGE_METERING_v1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# Usage/Metering v1 — Events, Rollups, Limits",
            "## 0) Kanonische Referenzen (nicht duplizieren)",
            "## 3) Was wird gemessen? (Metric Catalog v1)",
            "## 5) Event-Schema v1 (usage_event)",
            "## 6) Rollups (Daily/Monthly) + Retention",
            "## 8) End-to-End Beispiel (Event → Rollup → Limit Check)",
            "## 9) Abhängigkeiten / Cross-Links",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Pflichtmarker fehlt: {marker}")

        for must_include in [
            "idempotency_key",
            "requests.analyze",
            "usage_events",
            "usage_rollups_daily",
            "usage_rollups_monthly",
            "#627",
            "#628",
        ]:
            self.assertIn(must_include, content, msg=f"Pflichtinhalt fehlt: {must_include}")

    def test_backlog_tracks_629_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn(
            "✅ #629 abgeschlossen (2026-03-01): Usage/Metering v1 in [`docs/USAGE_METERING_v1.md`](USAGE_METERING_v1.md) ergänzt",
            backlog,
        )


if __name__ == "__main__":
    unittest.main()
