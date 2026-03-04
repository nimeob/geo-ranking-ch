import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestDevEnvReadinessChecklistDocs(unittest.TestCase):
    def test_checklist_doc_exists_with_required_markers(self):
        checklist_path = REPO_ROOT / "docs" / "DEV_ENV_READINESS_CHECKLIST.md"
        self.assertTrue(checklist_path.is_file(), msg="docs/DEV_ENV_READINESS_CHECKLIST.md fehlt")

        content = checklist_path.read_text(encoding="utf-8")
        required_markers = [
            "# Dev Environment Readiness Checklist",
            "## 1) Readiness-Checklist (Quick Gate)",
            "## 2) Copy/Paste Verify-Kommandos",
            "## 3) Häufige Fehlerbilder (mit Fix)",
            "### Fehlerbild A",
            "### Fehlerbild B",
            "### Fehlerbild C",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt im Readiness-Doc: {marker}")

    def test_contributing_and_readme_link_to_checklist(self):
        contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("docs/DEV_ENV_READINESS_CHECKLIST.md", contributing)
        self.assertIn("docs/DEV_ENV_READINESS_CHECKLIST.md", readme)


if __name__ == "__main__":
    unittest.main()
