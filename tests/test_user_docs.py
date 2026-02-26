import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestUserDocumentation(unittest.TestCase):
    def test_api_usage_guide_exists_with_core_sections(self):
        api_usage_path = REPO_ROOT / "docs" / "user" / "api-usage.md"
        self.assertTrue(api_usage_path.is_file(), msg="docs/user/api-usage.md fehlt")

        content = api_usage_path.read_text(encoding="utf-8")
        required_markers = [
            "# API Usage Guide",
            "## Endpoint-Referenz",
            "## `POST /analyze`",
            "## Authentifizierung",
            "## Request-ID-Korrelation",
            "## Statuscodes und Fehlerbilder",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt im API-Guide: {marker}")

    def test_user_docs_index_links_to_api_usage(self):
        user_index = (REPO_ROOT / "docs" / "user" / "README.md").read_text(encoding="utf-8")
        self.assertIn("[API Usage Guide](./api-usage.md)", user_index)

        getting_started = (REPO_ROOT / "docs" / "user" / "getting-started.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("[API Usage Guide](./api-usage.md)", getting_started)

    def test_root_readme_contains_thematic_webservice_feature_list(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("### Webservice-Features (thematisch geordnet)", readme)
        self.assertIn("**API-Grundfunktionen**", readme)
        self.assertIn("**Sicherheit & Zugriff**", readme)
        self.assertIn("**Robuste API-Eingänge**", readme)
        self.assertIn("**Betrieb & Nachvollziehbarkeit**", readme)
        self.assertIn("docs/user/api-usage.md", readme)


if __name__ == "__main__":
    unittest.main()
