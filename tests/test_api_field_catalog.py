import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "scripts" / "validate_field_catalog.py"
CONTRACT_DOC = REPO_ROOT / "docs" / "api" / "contract-v1.md"


class TestApiFieldCatalog(unittest.TestCase):
    def test_validator_script_passes(self):
        proc = subprocess.run(
            [sys.executable, str(VALIDATOR)],
            cwd=str(REPO_ROOT),
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            self.fail(
                "field_catalog validator failed:\n"
                f"stdout:\n{proc.stdout}\n"
                f"stderr:\n{proc.stderr}"
            )

    def test_contract_doc_references_field_catalog(self):
        content = CONTRACT_DOC.read_text(encoding="utf-8")
        markers = [
            "docs/api/field_catalog.json",
            "scripts/validate_field_catalog.py",
            "analyze.response.grouped.success.json",
        ]
        for marker in markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in contract-v1.md: {marker}")


if __name__ == "__main__":
    unittest.main()
