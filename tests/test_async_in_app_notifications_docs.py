import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestAsyncInAppNotificationsDocs(unittest.TestCase):
    def test_notification_doc_contains_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "api" / "async-in-app-notifications-v1.md"
        self.assertTrue(doc_path.is_file(), msg="Notification-Pipeline-Doku fehlt")

        content = doc_path.read_text(encoding="utf-8")
        for marker in (
            "Issue: #601 (Parent #594)",
            "GET /analyze/jobs/{job_id}/notifications",
            "state.notifications",
            "dedupe_key",
            "async.job.completed",
            "async.job.failed",
            "X-Org-Id",
        ):
            self.assertIn(marker, content, msg=f"Pflichtmarker fehlt: {marker}")


if __name__ == "__main__":
    unittest.main()
