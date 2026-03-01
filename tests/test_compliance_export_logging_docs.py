import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestComplianceExportLoggingDocs(unittest.TestCase):
    def test_export_logging_standard_doc_exists_with_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "compliance" / "EXPORT_LOGGING_STANDARD_V1.md"
        self.assertTrue(
            doc_path.is_file(),
            msg="docs/compliance/EXPORT_LOGGING_STANDARD_V1.md fehlt",
        )

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# Minimum-Compliance-Set — Export-Logging-Standard v1",
            "## Verbindliche Pflichtfelder (wer/wann/kanal)",
            "actor",
            "exported_at_utc",
            "channel",
            "artifacts/compliance/export/export_log_v1.jsonl",
            "Issue #525",
        ]
        for marker in required_markers:
            self.assertIn(
                marker,
                content,
                msg=f"Marker fehlt im Export-Logging-Standard: {marker}",
            )

    def test_backlog_tracks_issue_525_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("### BL-342 — Minimum-Compliance-Set (Governance-Rollout)", backlog)
        self.assertIn(
            "#525 — Export-Logging implementieren (wer/wann/Kanal) (abgeschlossen 2026-03-01)",
            backlog,
        )


if __name__ == "__main__":
    unittest.main()
