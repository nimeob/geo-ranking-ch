import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GUIDE_PATH = REPO_ROOT / "docs" / "api" / "API_DATA_ONLY_UI_MIGRATION_GUIDE.md"


class TestApiDataOnlyMigrationGuideDocs(unittest.TestCase):
    def test_guide_exists_with_required_sections(self):
        self.assertTrue(GUIDE_PATH.is_file(), msg="API Data-only Migrationsguide fehlt")

        content = GUIDE_PATH.read_text(encoding="utf-8")
        required_markers = [
            "# API Data-only Guide + UI-Migrationsanleitung (Issue #1176)",
            "## 1) Data-only Contract (verbindlich)",
            "## 2) UI-Ownership (verbindlich)",
            "## 3) Breaking Changes und Deprecation-Signale",
            "## 4) Migrationsbeispiele (before -> after)",
            "## 5) Onboarding-Checkliste (30 Minuten)",
            "`POST /analyze`",
            "`GET /analyze/history`",
            "`GET /debug/trace`",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt im Guide: {marker}")

    def test_readme_and_architecture_link_to_guide(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        architecture = (REPO_ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")

        self.assertIn(
            "docs/api/API_DATA_ONLY_UI_MIGRATION_GUIDE.md",
            readme,
            msg="README muss auf den API Data-only Migrationsguide verlinken",
        )
        self.assertIn(
            "api/API_DATA_ONLY_UI_MIGRATION_GUIDE.md",
            architecture,
            msg="ARCHITECTURE muss auf den API Data-only Migrationsguide verlinken",
        )


if __name__ == "__main__":
    unittest.main()
