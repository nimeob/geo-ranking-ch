import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestAsyncRetentionCleanupDocs(unittest.TestCase):
    def test_retention_cleanup_doc_contains_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "api" / "async-retention-cleanup-v1.md"
        self.assertTrue(doc_path.is_file(), msg="Retention-Cleanup-Doku fehlt")

        content = doc_path.read_text(encoding="utf-8")
        for marker in (
            "Issue: #600 (Parent #594)",
            "cleanup_retention",
            "scripts/run_async_retention_cleanup.py",
            "ASYNC_JOB_RESULTS_RETENTION_SECONDS",
            "ASYNC_JOB_EVENTS_RETENTION_SECONDS",
            "terminale Jobs (`completed|failed|canceled`)",
        ):
            self.assertIn(marker, content, msg=f"Pflichtmarker fehlt: {marker}")


if __name__ == "__main__":
    unittest.main()
