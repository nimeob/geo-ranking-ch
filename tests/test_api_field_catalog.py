import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "scripts" / "validate_field_catalog.py"
CONTRACT_DOC = REPO_ROOT / "docs" / "api" / "contract-v1.md"
FIELD_REFERENCE_DOC = REPO_ROOT / "docs" / "api" / "field-reference-v1.md"
FIELD_CATALOG = REPO_ROOT / "docs" / "api" / "field_catalog.json"


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
            "docs/api/field-reference-v1.md",
            "scripts/validate_field_catalog.py",
            "analyze.response.grouped.success.json",
            "location-intelligence.response.success.address.json",
        ]
        for marker in markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in contract-v1.md: {marker}")

    def test_response_shape_examples_from_catalog_exist(self):
        catalog = json.loads(FIELD_CATALOG.read_text(encoding="utf-8"))
        response_shapes = catalog.get("response_shapes")
        self.assertIsInstance(response_shapes, dict)
        self.assertEqual(set(response_shapes.keys()), {"legacy", "grouped"})

        for shape, rel_path in response_shapes.items():
            self.assertIsInstance(rel_path, str, msg=f"Ungültiger Pfadtyp für {shape}")
            self.assertTrue(rel_path.strip(), msg=f"Leerer Pfad für {shape}")

            path = (REPO_ROOT / rel_path).resolve()
            self.assertTrue(path.is_file(), msg=f"Fehlende Beispielpayload für {shape}: {rel_path}")

    def test_human_readable_field_reference_contains_both_shapes(self):
        content = FIELD_REFERENCE_DOC.read_text(encoding="utf-8")
        markers = [
            "Legacy-Shape (`response_shape=legacy`)",
            "Grouped-Shape (`response_shape=grouped`)",
            "result.input_mode",
            "result.data.entity.query",
            "intelligence_mode=extended|risk",
            "docs/api/field_catalog.json",
        ]
        for marker in markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in field-reference-v1.md: {marker}")


if __name__ == "__main__":
    unittest.main()
