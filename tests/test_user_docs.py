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

    def test_configuration_env_guide_exists_with_core_sections(self):
        configuration_path = REPO_ROOT / "docs" / "user" / "configuration-env.md"
        self.assertTrue(configuration_path.is_file(), msg="docs/user/configuration-env.md fehlt")

        content = configuration_path.read_text(encoding="utf-8")
        required_markers = [
            "# Configuration / ENV Guide",
            "## 1) Webservice (`src/web_service.py`)",
            "## 2) Remote-Smoke (`scripts/run_remote_api_smoketest.sh`)",
            "## 3) Stabilitätslauf (`scripts/run_remote_api_stability_check.sh`)",
            "## 4) Konfigurationsbeispiele",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt im Configuration/ENV-Guide: {marker}")

    def test_user_docs_index_links_to_core_guides(self):
        user_index = (REPO_ROOT / "docs" / "user" / "README.md").read_text(encoding="utf-8")
        self.assertIn("[Configuration / ENV](./configuration-env.md)", user_index)
        self.assertIn("[API Usage Guide](./api-usage.md)", user_index)
        self.assertIn("[Troubleshooting](./troubleshooting.md)", user_index)
        self.assertIn("[Operations Quick Guide](./operations-runbooks.md)", user_index)

        getting_started = (REPO_ROOT / "docs" / "user" / "getting-started.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("[Configuration / ENV](./configuration-env.md)", getting_started)
        self.assertIn("[API Usage Guide](./api-usage.md)", getting_started)
        self.assertIn("[Troubleshooting](./troubleshooting.md)", getting_started)
        self.assertIn("[Operations Quick Guide](./operations-runbooks.md)", getting_started)

    def test_troubleshooting_guide_exists_with_core_sections(self):
        troubleshooting_path = REPO_ROOT / "docs" / "user" / "troubleshooting.md"
        self.assertTrue(troubleshooting_path.is_file(), msg="docs/user/troubleshooting.md fehlt")

        content = troubleshooting_path.read_text(encoding="utf-8")
        required_markers = [
            "# Troubleshooting",
            "## 401 `unauthorized`",
            "## 400 `bad_request`",
            "## 504 `timeout`",
            "## Smoke/Stability-Checks für reproduzierbare Diagnose",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt im Troubleshooting-Guide: {marker}")

    def test_operations_quick_guide_exists_with_core_sections(self):
        operations_path = REPO_ROOT / "docs" / "user" / "operations-runbooks.md"
        self.assertTrue(operations_path.is_file(), msg="docs/user/operations-runbooks.md fehlt")

        content = operations_path.read_text(encoding="utf-8")
        required_markers = [
            "# Operations Quick Guide (BL-19.6)",
            "## 1) Daily Quick Check (2–5 Minuten)",
            "## 2) Reproduzierbarer Smoke-Test (`/analyze`)",
            "## 3) Kurzer Stabilitätslauf",
            "## 5) Incident-Minirunbook",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt im Operations-Guide: {marker}")

    def test_root_readme_contains_thematic_webservice_feature_list(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("### Webservice-Features (thematisch geordnet)", readme)
        self.assertIn("**API-Grundfunktionen**", readme)
        self.assertIn("**Sicherheit & Zugriff**", readme)
        self.assertIn("**Robuste API-Eingänge**", readme)
        self.assertIn("**Betrieb & Nachvollziehbarkeit**", readme)
        self.assertIn("docs/user/configuration-env.md", readme)
        self.assertIn("docs/user/api-usage.md", readme)
        self.assertIn("docs/user/operations-runbooks.md", readme)


if __name__ == "__main__":
    unittest.main()
