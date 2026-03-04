import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestApiUiBoundaryContractDocs(unittest.TestCase):
    def test_architecture_contains_versioned_boundary_contract(self):
        architecture = (REPO_ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
        required_markers = [
            "## 7) API/UI Boundary Contract (v1)",
            "Boundary-Version:",
            "api-ui-boundary/v1",
            "### 7.2 Verbindliche Ownership-Regeln",
            "### 7.3 Route- und Modulkonventionen (v1)",
            "scripts/check_bl31_service_boundaries.py",
        ]
        for marker in required_markers:
            self.assertIn(marker, architecture, msg=f"Marker fehlt in docs/ARCHITECTURE.md: {marker}")

    def test_pr_template_contains_boundary_checklist(self):
        template_path = REPO_ROOT / ".github" / "pull_request_template.md"
        self.assertTrue(template_path.is_file(), msg=".github/pull_request_template.md fehlt")

        template = template_path.read_text(encoding="utf-8")
        required_checks = [
            "## Boundary-Check (verbindlich)",
            "Keine neuen Cross-Layer-Imports",
            "Routen folgen der Ownership-Matrix",
            "Follow-up-Issue inkl. Migrations-/Sunset-Plan",
        ]
        for marker in required_checks:
            self.assertIn(marker, template, msg=f"Boundary-Check fehlt im PR-Template: {marker}")


if __name__ == "__main__":
    unittest.main()
