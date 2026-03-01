from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestPrFastGatesConfig(unittest.TestCase):
    def _read(self, relative_path: str) -> str:
        return (REPO_ROOT / relative_path).read_text(encoding="utf-8")

    def test_contract_smoke_workflow_triggers_on_pull_request(self):
        content = self._read(".github/workflows/contract-tests.yml")
        self.assertIn("name: contract-smoke", content)
        self.assertIn("on:", content)
        self.assertIn("pull_request:", content)
        self.assertIn("workflow_dispatch:", content)
        self.assertIn("jobs:", content)
        self.assertIn("contract-smoke:", content)

    def test_docs_link_guard_workflow_triggers_on_pull_request(self):
        content = self._read(".github/workflows/docs-quality.yml")
        self.assertIn("name: docs-link-guard", content)
        self.assertIn("on:", content)
        self.assertIn("pull_request:", content)
        self.assertIn("workflow_dispatch:", content)
        self.assertIn("jobs:", content)
        self.assertIn("docs-link-guard:", content)

    def test_operations_required_checks_documented(self):
        content = self._read("docs/OPERATIONS.md")
        self.assertIn("`contract-smoke` (**required**)", content)
        self.assertIn("`docs-link-guard` (**required", content)


if __name__ == "__main__":
    unittest.main()
