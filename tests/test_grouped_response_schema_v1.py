import json
import unittest
from pathlib import Path
from typing import Any

from src.web_service import _grouped_api_result


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "docs" / "api" / "schemas" / "v1" / "analyze.grouped.response.schema.json"
CORE_PATHS_PATH = REPO_ROOT / "docs" / "api" / "schemas" / "v1" / "analyze.grouped.core-paths.v1.json"
GROUPED_SUCCESS_EXAMPLE = (
    REPO_ROOT / "docs" / "api" / "examples" / "current" / "analyze.response.grouped.success.json"
)
GROUPED_PARTIAL_EXAMPLE = (
    REPO_ROOT / "docs" / "api" / "examples" / "current" / "analyze.response.grouped.partial-disabled.json"
)
GROUPED_ADDITIVE_BEFORE_EXAMPLE = (
    REPO_ROOT / "docs" / "api" / "examples" / "current" / "analyze.response.grouped.additive-before.json"
)
GROUPED_ADDITIVE_AFTER_EXAMPLE = (
    REPO_ROOT / "docs" / "api" / "examples" / "current" / "analyze.response.grouped.additive-after.json"
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _get_by_dotted_path(payload: Any, dotted_path: str) -> Any:
    current = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(dotted_path)
        current = current[part]
    return current


def _assert_type(case: unittest.TestCase, value: Any, expected_type: str, path: str) -> None:
    if expected_type == "string":
        case.assertIsInstance(value, str, msg=f"{path} muss string sein")
        case.assertTrue(value.strip(), msg=f"{path} darf nicht leer sein")
    elif expected_type == "number":
        case.assertIsInstance(value, (int, float), msg=f"{path} muss number sein")
    else:
        case.fail(f"Unbekannter expected_type in core-paths-Datei: {expected_type}")


class TestGroupedResponseSchemaV1(unittest.TestCase):
    def test_schema_and_core_paths_files_exist(self):
        for path in (SCHEMA_PATH, CORE_PATHS_PATH):
            self.assertTrue(path.is_file(), msg=f"Fehlendes Artefakt: {path}")
            payload = _read_json(path)
            self.assertIsInstance(payload, dict)

    def test_schema_declares_stable_core_structure_and_additive_extension_points(self):
        schema = _read_json(SCHEMA_PATH)

        self.assertEqual(schema.get("type"), "object")
        self.assertIn("result", schema.get("properties", {}))
        self.assertIn("result", schema.get("required", []))

        result = schema["properties"]["result"]
        self.assertIn("status", result.get("required", []))
        self.assertIn("data", result.get("required", []))
        self.assertTrue(result.get("additionalProperties"), msg="result muss additiv erweiterbar bleiben")

        status = result["properties"]["status"]
        self.assertIn("quality", status.get("required", []))
        self.assertIn("source_health", status.get("required", []))
        self.assertIn("source_meta", status.get("required", []))
        self.assertTrue(status.get("additionalProperties"), msg="status muss additiv erweiterbar bleiben")

        dictionary = status.get("properties", {}).get("dictionary")
        self.assertIsInstance(dictionary, dict, msg="status.dictionary muss als additiver Envelope spezifiziert sein")
        self.assertEqual(set(dictionary.get("required", [])), {"version", "etag"})
        self.assertIn("domains", dictionary.get("properties", {}))

        data = result["properties"]["data"]
        self.assertIn("entity", data.get("required", []))
        self.assertIn("modules", data.get("required", []))
        self.assertIn("by_source", data.get("required", []))
        self.assertTrue(data.get("additionalProperties"), msg="data muss additiv erweiterbar bleiben")

    def test_core_paths_exist_and_type_match_in_current_examples(self):
        core_paths = _read_json(CORE_PATHS_PATH).get("core_paths", [])
        self.assertTrue(core_paths, msg="core_paths darf nicht leer sein")

        for payload_path in (GROUPED_SUCCESS_EXAMPLE, GROUPED_PARTIAL_EXAMPLE):
            payload = _read_json(payload_path)
            for spec in core_paths:
                path = spec["path"]
                expected_type = spec["type"]
                value = _get_by_dotted_path(payload, path)
                _assert_type(self, value, expected_type, path)

    def test_additive_before_after_examples_keep_core_paths_stable(self):
        core_paths = _read_json(CORE_PATHS_PATH).get("core_paths", [])
        before = _read_json(GROUPED_ADDITIVE_BEFORE_EXAMPLE)
        after = _read_json(GROUPED_ADDITIVE_AFTER_EXAMPLE)

        for spec in core_paths:
            path = spec["path"]
            before_value = _get_by_dotted_path(before, path)
            after_value = _get_by_dotted_path(after, path)
            self.assertEqual(
                before_value,
                after_value,
                msg=f"Kernpfad wurde trotz additiver Erweiterung verändert: {path}",
            )

    def test_runtime_grouping_preserves_core_paths(self):
        report = {
            "query": "Bahnhofstrasse 1, 8001 Zürich",
            "matched_address": "Bahnhofstrasse 1, 8001 Zürich",
            "ids": {"egid": "123"},
            "coordinates": {"lat": 47.3769, "lon": 8.5417},
            "match": {"selected_score": 0.99, "candidate_count": 3, "status": "ok"},
            "confidence": {"score": 92, "max": 100, "level": "high"},
            "sources": {"geoadmin_search": {"status": "ok", "records": 1}},
            "source_attribution": {"match": ["geoadmin_search"]},
        }

        grouped = {"ok": True, "request_id": "runtime-schema-v1", "result": _grouped_api_result(report)}
        core_paths = _read_json(CORE_PATHS_PATH).get("core_paths", [])

        for spec in core_paths:
            path = spec["path"]
            value = _get_by_dotted_path(grouped, path)
            _assert_type(self, value, spec["type"], path)


    def test_derived_from_projection_is_added_when_field_provenance_present(self):
        report = {
            "query": "Bahnhofstrasse 1, 8001 Zürich",
            "matched_address": "Bahnhofstrasse 1, 8001 Zürich",
            "ids": {"egid": "123"},
            "coordinates": {"lat": 47.3769, "lon": 8.5417},
            "match": {"selected_score": 0.99, "candidate_count": 3, "status": "ok"},
            "confidence": {"score": 92, "max": 100, "level": "high"},
            "sources": {"geoadmin_search": {"status": "ok", "records": 1}},
            "source_attribution": {"match": ["geoadmin_search"]},
            "field_provenance": {
                "building.baujahr": {
                    "sources": ["geoadmin_search"],
                    "primary_source": "geoadmin_search",
                    "present": True,
                    "authority": "federal",
                    "notes": "extra keys must not leak into derived_from",
                }
            },
        }

        grouped = _grouped_api_result(report)
        source_meta = grouped.get("status", {}).get("source_meta", {})

        self.assertIn("field_provenance", source_meta)
        self.assertIn("derived_from", source_meta)

        self.assertEqual(
            source_meta["derived_from"].get("building.baujahr"),
            {
                "sources": ["geoadmin_search"],
                "primary_source": "geoadmin_search",
                "present": True,
                "authority": "federal",
            },
        )


if __name__ == "__main__":
    unittest.main()
