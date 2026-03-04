import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SUNSET = "Tue, 30 Jun 2026 23:59:59 GMT"


class TestApiDeprecationMappingDocs(unittest.TestCase):
    def test_architecture_contains_deprecation_mapping_table(self):
        content = (REPO_ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
        self.assertIn("#### API Deprecation Mapping (Dev)", content)
        self.assertIn("`GET /history`", content)
        self.assertIn("`GET /analyze/history` (front-facing usage)", content)
        self.assertIn("`GET /trace` (legacy alias)", content)
        self.assertIn("`GET /login`, `/signin`, `/sign-in`", content)
        self.assertIn(SUNSET, content)
        self.assertIn('rel="deprecation"', content)
        self.assertIn("Legacy-Trace-Contract (`GET /trace` auf API", content)
        self.assertIn('Warning: 299 - "Legacy trace alias on API is deprecated and removed: use /debug/trace?request_id=<id>."', content)
        self.assertIn('deprecation.scope="trace-debug-legacy-alias"', content)

    def test_external_direct_access_doc_uses_same_sunset(self):
        content = (
            REPO_ROOT
            / "docs"
            / "compliance"
            / "EXTERNAL_DIRECT_ACCESS_CONTROL_V1.md"
        ).read_text(encoding="utf-8")
        self.assertIn(SUNSET, content)
        self.assertIn('rel="deprecation"', content)


if __name__ == "__main__":
    unittest.main()
