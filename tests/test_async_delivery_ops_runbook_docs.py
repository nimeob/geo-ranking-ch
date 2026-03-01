import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestAsyncDeliveryOpsRunbookDocs(unittest.TestCase):
    def test_runbook_contains_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "api" / "async-delivery-ops-runbook-v1.md"
        self.assertTrue(doc_path.is_file(), msg="Async-Delivery Ops-Runbook fehlt")

        content = doc_path.read_text(encoding="utf-8")
        for marker in (
            "Issue: #602 (Parent #594)",
            "GET /analyze/results/{result_id}",
            "GET /analyze/jobs/{job_id}/notifications",
            "scripts/run_async_retention_cleanup.py",
            "Monitoring-Mindestmetriken + Alert-Hinweise",
            "Smoke-Checkliste Staging",
            "Smoke-Checkliste Prod",
            "async_result_permalink_http_5xx_rate_5m",
            "async_retention_cleanup_exit_code",
            "async_notifications_terminal_jobs_without_in_app_10m",
        ):
            self.assertIn(marker, content, msg=f"Pflichtmarker fehlt: {marker}")

    def test_operations_references_async_delivery_runbook(self):
        operations = (REPO_ROOT / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")
        self.assertIn(
            "api/async-delivery-ops-runbook-v1.md",
            operations,
            msg="OPERATIONS.md verweist nicht auf das Async-Delivery-Runbook",
        )


if __name__ == "__main__":
    unittest.main()
