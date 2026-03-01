import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestAsyncAnalyzeRuntimeSkeletonDocs(unittest.TestCase):
    def test_runtime_skeleton_docs_and_schema_exist_with_required_markers(self):
        runtime_doc = REPO_ROOT / "docs" / "api" / "async-analyze-runtime-skeleton-v1.md"
        schema_doc = REPO_ROOT / "docs" / "sql" / "async_jobs_schema_v1.sql"

        self.assertTrue(runtime_doc.is_file(), msg="Runtime-Skeleton-Doku fehlt")
        self.assertTrue(schema_doc.is_file(), msg="SQL-Basisschema fehlt")

        runtime_content = runtime_doc.read_text(encoding="utf-8")
        schema_content = schema_doc.read_text(encoding="utf-8")

        for marker in (
            "Issue: #592 (Parent #588)",
            "options.async_mode.requested",
            "GET /analyze/jobs/{job_id}",
            "GET /analyze/results/{result_id}",
            "runtime/async_jobs/store.v1.json",
        ):
            self.assertIn(marker, runtime_content, msg=f"Pflichtmarker fehlt: {marker}")

        for token in (
            "CREATE TABLE IF NOT EXISTS jobs",
            "CREATE TABLE IF NOT EXISTS job_events",
            "CREATE TABLE IF NOT EXISTS job_results",
            "idx_jobs_org_status_updated",
            "idx_job_results_job_seq",
        ):
            self.assertIn(token, schema_content, msg=f"Pflichttoken fehlt: {token}")

    def test_worker_pipeline_docs_exist_with_cancel_and_retry_markers(self):
        pipeline_doc = REPO_ROOT / "docs" / "api" / "async-analyze-worker-pipeline-v1.md"
        self.assertTrue(pipeline_doc.is_file(), msg="Worker-Pipeline-Doku fehlt")

        content = pipeline_doc.read_text(encoding="utf-8")
        for marker in (
            "Issue: #593 (Parent #588)",
            "POST /analyze/jobs/{job_id}/cancel",
            "job.partial",
            "retry_hint",
            "worker-ausführung",
        ):
            self.assertIn(marker, content, msg=f"Pflichtmarker fehlt: {marker}")

    def test_backlog_tracks_issue_593_599_600_progress(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("#593 abgeschlossen", backlog)
        self.assertIn("#599 abgeschlossen", backlog)
        self.assertIn("#600 abgeschlossen", backlog)
        self.assertIn("BL-30-Follow-up #602", backlog)
        self.assertIn("docs/api/async-analyze-worker-pipeline-v1.md", backlog)
        self.assertIn("docs/api/async-retention-cleanup-v1.md", backlog)


if __name__ == "__main__":
    unittest.main()
