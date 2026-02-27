import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestOpenClawAutomationMappingDocs(unittest.TestCase):
    def test_mapping_doc_exists_with_required_workflows_and_policies(self):
        doc_path = REPO_ROOT / "docs" / "automation" / "openclaw-job-mapping.md"
        self.assertTrue(doc_path.is_file(), msg="docs/automation/openclaw-job-mapping.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-20.y.wp2 — OpenClaw-Mapping für migrierbare GitHub-Workflows",
            "## Standard-Policy (für alle OpenClaw-Jobs)",
            "geo-ranking-contract-tests-surrogate",
            "geo-ranking-crawler-regression-surrogate",
            "geo-ranking-docs-quality-surrogate",
            "geo-ranking-worker-claim-reconciler",
            "reports/automation/contract-tests/",
            "reports/automation/crawler-regression/",
            "reports/automation/docs-quality/",
            "reports/automation/worker-claim-priority/",
            "scripts/run_openclaw_migrated_job.py",
            "#223",
            "#224",
        ]

        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in openclaw-job-mapping.md: {marker}")

    def test_operations_references_openclaw_mapping_doc(self):
        ops_path = REPO_ROOT / "docs" / "OPERATIONS.md"
        self.assertTrue(ops_path.is_file(), msg="docs/OPERATIONS.md fehlt")

        content = ops_path.read_text(encoding="utf-8")
        self.assertIn(
            "docs/automation/openclaw-job-mapping.md",
            content,
            msg="OPERATIONS.md verweist nicht auf das OpenClaw-Mapping",
        )
        self.assertIn(
            "scripts/run_openclaw_migrated_job.py",
            content,
            msg="OPERATIONS.md dokumentiert den OpenClaw-Migrationsrunner nicht",
        )


if __name__ == "__main__":
    unittest.main()
