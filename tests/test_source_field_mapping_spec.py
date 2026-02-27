import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "scripts" / "validate_source_field_mapping_spec.py"
SCHEMA = REPO_ROOT / "docs" / "mapping" / "source-field-mapping.schema.json"
SPEC = REPO_ROOT / "docs" / "mapping" / "source-field-mapping.ch.v1.json"


class TestSourceFieldMappingSpec(unittest.TestCase):
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
                "source-field-mapping validator failed:\n"
                f"stdout:\n{proc.stdout}\n"
                f"stderr:\n{proc.stderr}"
            )

    def test_schema_and_spec_files_exist_and_match_basic_contract(self):
        self.assertTrue(SCHEMA.is_file(), msg="Schema fehlt: docs/mapping/source-field-mapping.schema.json")
        self.assertTrue(SPEC.is_file(), msg="Spec fehlt: docs/mapping/source-field-mapping.ch.v1.json")

        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        spec = json.loads(SPEC.read_text(encoding="utf-8"))

        required = set(schema.get("required", []))
        self.assertEqual(
            required,
            {
                "spec_version",
                "spec_name",
                "generated_from",
                "updated_at",
                "transform_rules",
                "sources",
            },
        )

        for key in required:
            self.assertIn(key, spec, msg=f"Spec-Feld fehlt: {key}")

    def test_spec_contains_required_core_sources(self):
        spec = json.loads(SPEC.read_text(encoding="utf-8"))

        sources = spec.get("sources", [])
        source_names = {
            entry.get("source")
            for entry in sources
            if isinstance(entry, dict) and isinstance(entry.get("source"), str)
        }

        for required_source in ("geoadmin_search", "geoadmin_gwr", "bfs_heating_layer"):
            self.assertIn(required_source, source_names, msg=f"Pflichtquelle fehlt: {required_source}")


if __name__ == "__main__":
    unittest.main()
