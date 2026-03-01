import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestAsyncAnalyzeDomainDesignV1Docs(unittest.TestCase):
    def test_doc_contains_required_sections_and_markers(self):
        doc_path = REPO_ROOT / "docs" / "api" / "async-analyze-domain-design-v1.md"
        self.assertTrue(
            doc_path.is_file(),
            msg="docs/api/async-analyze-domain-design-v1.md fehlt",
        )

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# Async-Analyze Domain-Design v1 (GTM Follow-up)",
            "Issue: #587 (Parent #577)",
            "## 1) Job-State-Machine (verbindlich v1)",
            "## 2) Datenmodell v1 (`jobs`, `job_events`, `job_results`, `notifications`)",
            "## 3) Progress-/Chunking-Strategie + Partial Results",
            "## 4) UX-Flow (Progress, Completion, Result-Page)",
            "## 5) API-/Eventing-Schnittpunkte (Vorbereitung für Implementierung)",
            "## 6) DoD-Abdeckung (#587)",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Pflichtmarker fehlt: {marker}")

        required_tokens = [
            "queued",
            "running",
            "partial",
            "completed",
            "failed",
            "canceled",
            "job_id",
            "result_id",
            "progress_percent",
            "POST /analyze",
            "GET /analyze/jobs/{job_id}",
            "GET /analyze/results/{result_id}",
            "POST /analyze/jobs/{job_id}/cancel",
            "api.analyze.job.completed",
            "idx_jobs_org_status_updated",
        ]
        for token in required_tokens:
            self.assertIn(token, content, msg=f"Pflichttoken fehlt: {token}")

    def test_backlog_tracks_issue_587_completion_and_next_step(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("#587 abgeschlossen", backlog)
        self.assertIn(
            "[`docs/api/async-analyze-domain-design-v1.md`](api/async-analyze-domain-design-v1.md)",
            backlog,
        )
        self.assertIn("#592/#593/#594", backlog)


if __name__ == "__main__":
    unittest.main()
