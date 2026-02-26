import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DOC = REPO_ROOT / "docs" / "api" / "contract-v1.md"
SCHEMA_DIR = REPO_ROOT / "docs" / "api" / "schemas" / "v1"
EXAMPLE_DIR = REPO_ROOT / "docs" / "api" / "examples" / "v1"


class TestApiContractV1(unittest.TestCase):
    def test_contract_doc_contains_required_sections(self):
        self.assertTrue(CONTRACT_DOC.is_file(), msg="docs/api/contract-v1.md fehlt")
        content = CONTRACT_DOC.read_text(encoding="utf-8")

        markers = [
            "# BL-20.1.a — API Contract v1 (Schemas + Fehlercodes)",
            "## 1) Versionierungspfad (verbindlich)",
            "## 2) JSON-Schemas (Quelle der Wahrheit)",
            "## 4) Fehlercode-Matrix (v1)",
            "## 5) Beispielpayloads im Repo",
            "/api/v1/location-intelligence",
            "bad_request",
            "validation_failed",
            "upstream_error",
        ]
        for marker in markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in contract-v1.md: {marker}")

    def test_schema_files_exist_and_are_valid_json(self):
        schema_paths = [
            SCHEMA_DIR / "location-intelligence.request.schema.json",
            SCHEMA_DIR / "location-intelligence.response.schema.json",
            SCHEMA_DIR / "error.response.schema.json",
        ]

        for schema_path in schema_paths:
            self.assertTrue(schema_path.is_file(), msg=f"Schema fehlt: {schema_path}")
            payload = json.loads(schema_path.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("type"), "object")
            self.assertIn("title", payload)
            self.assertIn("$schema", payload)

    def test_examples_exist_and_match_minimal_contract_shape(self):
        req_address = json.loads(
            (EXAMPLE_DIR / "location-intelligence.request.address.json").read_text(encoding="utf-8")
        )
        req_point = json.loads(
            (EXAMPLE_DIR / "location-intelligence.request.point.json").read_text(encoding="utf-8")
        )
        resp_ok = json.loads(
            (EXAMPLE_DIR / "location-intelligence.response.success.address.json").read_text(
                encoding="utf-8"
            )
        )
        resp_err = json.loads(
            (EXAMPLE_DIR / "location-intelligence.response.error.bad-request.json").read_text(
                encoding="utf-8"
            )
        )

        # Request (address)
        self.assertEqual(req_address["input"]["mode"], "address")
        self.assertTrue(req_address["input"].get("address"))
        self.assertIn("requested_modules", req_address)
        self.assertGreaterEqual(len(req_address["requested_modules"]), 1)

        # Request (point)
        self.assertEqual(req_point["input"]["mode"], "point")
        self.assertIn("lat", req_point["input"]["point"])
        self.assertIn("lon", req_point["input"]["point"])

        # Success response
        self.assertTrue(resp_ok.get("ok"))
        self.assertEqual(resp_ok.get("api_version"), "v1")
        result = resp_ok.get("result") or {}
        for field in [
            "entity_id",
            "input_mode",
            "as_of",
            "confidence",
            "building_profile",
            "context_profile",
            "suitability_light",
            "explainability",
        ]:
            self.assertIn(field, result, msg=f"Result-Feld fehlt: {field}")
        self.assertIn("sources", (result.get("explainability") or {}))

        # Error response
        self.assertFalse(resp_err.get("ok"))
        self.assertEqual(resp_err.get("api_version"), "v1")
        error = resp_err.get("error") or {}
        self.assertEqual(error.get("code"), "bad_request")
        self.assertTrue(error.get("message"))


if __name__ == "__main__":
    unittest.main()
