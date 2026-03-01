import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestAsyncResultPermalinkTenantGuardDocs(unittest.TestCase):
    def test_doc_contains_required_contract_markers(self):
        doc_path = REPO_ROOT / "docs" / "api" / "async-result-permalink-tenant-guard-v1.md"
        self.assertTrue(doc_path.is_file(), msg="Result-Permalink-Tenant-Guard-Doku fehlt")

        content = doc_path.read_text(encoding="utf-8")
        for marker in (
            "Issue: #599 (Parent #594)",
            "GET /analyze/results/{result_id}",
            "X-Org-Id",
            "view=latest",
            "view=requested",
            "requested_result_id",
            "projection_mode",
        ):
            self.assertIn(marker, content, msg=f"Pflichtmarker fehlt: {marker}")


if __name__ == "__main__":
    unittest.main()
