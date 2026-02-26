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
SCORING_METHODOLOGY_DOC = REPO_ROOT / "docs" / "api" / "scoring_methodology.md"
GROUPED_PARTIAL_EXAMPLE = (
    REPO_ROOT / "docs" / "api" / "examples" / "current" / "analyze.response.grouped.partial-disabled.json"
)


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
            "docs/api/scoring_methodology.md",
            "scripts/validate_field_catalog.py",
            "analyze.response.grouped.success.json",
            "analyze.response.grouped.partial-disabled.json",
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
            "analyze.response.grouped.partial-disabled.json",
        ]
        for marker in markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in field-reference-v1.md: {marker}")

    def test_scoring_methodology_covers_all_scoring_paths_from_catalog(self):
        self.assertTrue(
            SCORING_METHODOLOGY_DOC.is_file(),
            msg="Scoring-Methodik fehlt: docs/api/scoring_methodology.md",
        )

        content = SCORING_METHODOLOGY_DOC.read_text(encoding="utf-8")
        markers = [
            "## 1) Score-Katalog",
            "Stabilitätsstatus",
            "docs/api/field_catalog.json",
            "result.status.quality.confidence.score",
            "result.suitability_light.score",
        ]
        for marker in markers:
            self.assertIn(
                marker,
                content,
                msg=f"Marker fehlt in scoring_methodology.md: {marker}",
            )

        catalog = json.loads(FIELD_CATALOG.read_text(encoding="utf-8"))
        scoring_paths = sorted(
            {
                field.get("path", "")
                for field in catalog.get("fields", [])
                if isinstance(field, dict)
                and isinstance(field.get("path"), str)
                and any(
                    keyword in field["path"]
                    for keyword in ("score", "risk", "rating", "confidence", "traffic_light")
                )
            }
        )
        self.assertTrue(scoring_paths, msg="Keine scoring-relevanten Feldpfade im Katalog gefunden")

        for path in scoring_paths:
            self.assertIn(
                f"`{path}`",
                content,
                msg=f"Scoring-Feldpfad fehlt in scoring_methodology.md: {path}",
            )

    def test_grouped_partial_example_documents_missing_or_disabled_data(self):
        self.assertTrue(
            GROUPED_PARTIAL_EXAMPLE.is_file(),
            msg="Edge-Case-Beispiel fehlt: analyze.response.grouped.partial-disabled.json",
        )
        payload = json.loads(GROUPED_PARTIAL_EXAMPLE.read_text(encoding="utf-8"))

        self.assertIs(payload.get("ok"), True)
        self.assertIsInstance(payload.get("request_id"), str)

        result = payload.get("result")
        self.assertIsInstance(result, dict)

        source_health = result.get("status", {}).get("source_health", {})
        self.assertIsInstance(source_health, dict)
        self.assertGreaterEqual(len(source_health), 2)

        source_states = {
            meta.get("status") for meta in source_health.values() if isinstance(meta, dict)
        }
        self.assertTrue(
            {"disabled", "missing"}.intersection(source_states),
            msg="Edge-Case-Beispiel muss mindestens eine deaktivierte oder fehlende Quelle ausweisen",
        )

        modules = result.get("data", {}).get("modules", {})
        self.assertIsInstance(modules, dict)
        self.assertNotIn(
            "intelligence",
            modules,
            msg="Edge-Case-Beispiel soll fehlendes Intelligence-Modul über Abwesenheit dokumentieren",
        )

        field_provenance = modules.get("field_provenance", {})
        self.assertIsInstance(field_provenance, dict)
        self.assertTrue(
            any(
                isinstance(meta, dict) and meta.get("present") is False
                for meta in field_provenance.values()
            ),
            msg="Edge-Case-Beispiel muss fehlende Felder via present=false dokumentieren",
        )

        by_source = result.get("data", {}).get("by_source", {})
        self.assertIsInstance(by_source, dict)
        empty_sources = [
            name
            for name, entry in by_source.items()
            if isinstance(entry, dict) and entry.get("data") == {}
        ]
        self.assertTrue(
            empty_sources,
            msg="Edge-Case-Beispiel muss mindestens eine Quelle mit leerem data-Objekt enthalten",
        )


if __name__ == "__main__":
    unittest.main()
