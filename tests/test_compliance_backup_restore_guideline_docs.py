import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestComplianceBackupRestoreGuidelineDocs(unittest.TestCase):
    def test_backup_restore_guideline_exists_with_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "compliance" / "BACKUP_RESTORE_GUIDELINE_V1.md"
        self.assertTrue(
            doc_path.is_file(),
            msg="docs/compliance/BACKUP_RESTORE_GUIDELINE_V1.md fehlt",
        )

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# Minimum-Compliance-Set — Backup/Restore-Guideline v1",
            "## Mindestanforderungen (RPO/RTO)",
            "## Backup-Policy (verbindlich)",
            "## Restore-Workflow (verbindlich)",
            "## Restore-Übung und Verifikation",
            "## Nachweisformat (verbindlich)",
            "reports/compliance/backup-restore/<YYYY>/<MM>/<restore_run_id>/",
            "Issue #526",
        ]

        for marker in required_markers:
            self.assertIn(
                marker,
                content,
                msg=f"Marker fehlt in Backup/Restore-Guideline: {marker}",
            )

    def test_backlog_tracks_issue_526_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("### BL-342 — Minimum-Compliance-Set (Governance-Rollout)", backlog)
        self.assertIn(
            "#526 — Backup/Restore-Guideline dokumentieren (abgeschlossen 2026-03-01)",
            backlog,
        )


if __name__ == "__main__":
    unittest.main()
