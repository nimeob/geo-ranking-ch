import json
import re
import unittest
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DOC = REPO_ROOT / "docs" / "api" / "contract-v1.md"
STABILITY_POLICY_DOC = REPO_ROOT / "docs" / "api" / "contract-stability-policy.md"
SCHEMA_DIR = REPO_ROOT / "docs" / "api" / "schemas" / "v1"
EXAMPLE_DIR = REPO_ROOT / "docs" / "api" / "examples" / "v1"
GOLDEN_DIR = REPO_ROOT / "tests" / "data" / "api_contract_v1"

_ALLOWED_MODULES = {
    "building_profile",
    "context_profile",
    "suitability_light",
    "explainability",
}
_ALLOWED_LANGUAGES = {"de", "en", "fr", "it"}
_ALLOWED_ERROR_CODES = {
    "bad_request",
    "unauthorized",
    "not_found",
    "validation_failed",
    "rate_limited",
    "upstream_error",
    "timeout",
    "internal",
}
_ALLOWED_EXPLAINABILITY_DIRECTIONS = {"pro", "contra", "neutral"}


def _is_non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_request_id_like(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if not (1 <= len(value) <= 128):
        return False
    if not value.isascii():
        return False
    if any(ch.isspace() for ch in value):
        return False
    return True


def _is_version(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"v[0-9]+", value))


def validate_request(payload: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["payload must be object"]

    allowed_top = {"request_id", "input", "requested_modules", "options"}
    unknown_top = set(payload.keys()) - allowed_top
    if unknown_top:
        errors.append(f"unknown top-level keys: {sorted(unknown_top)}")

    if "request_id" in payload and not _is_request_id_like(payload.get("request_id")):
        errors.append("request_id invalid")

    input_obj = payload.get("input")
    if not isinstance(input_obj, dict):
        errors.append("input must be object")
        input_obj = {}

    modules = payload.get("requested_modules")
    if not isinstance(modules, list) or not modules:
        errors.append("requested_modules must be non-empty array")
    else:
        if len(set(modules)) != len(modules):
            errors.append("requested_modules must be unique")
        for module in modules:
            if module not in _ALLOWED_MODULES:
                errors.append(f"requested_modules invalid value: {module}")

    mode = input_obj.get("mode")
    if mode not in {"address", "point"}:
        errors.append("input.mode invalid")

    input_allowed = {"mode", "address", "point"}
    input_unknown = set(input_obj.keys()) - input_allowed
    if input_unknown:
        errors.append(f"input contains unknown keys: {sorted(input_unknown)}")

    if mode == "address":
        address = input_obj.get("address")
        if not (_is_non_empty_str(address) and len(str(address).strip()) >= 3):
            errors.append("input.address required for mode=address")
    if mode == "point":
        point = input_obj.get("point")
        if not isinstance(point, dict):
            errors.append("input.point required for mode=point")
        else:
            lat = point.get("lat")
            lon = point.get("lon")
            if not isinstance(lat, (int, float)):
                errors.append("input.point.lat must be number")
            if not isinstance(lon, (int, float)):
                errors.append("input.point.lon must be number")
            if isinstance(lat, (int, float)) and not (45.0 <= float(lat) <= 48.5):
                errors.append("input.point.lat out of CH bounds")
            if isinstance(lon, (int, float)) and not (5.0 <= float(lon) <= 11.5):
                errors.append("input.point.lon out of CH bounds")

    options = payload.get("options")
    if options is not None:
        if not isinstance(options, dict):
            errors.append("options must be object")
        else:
            allowed_opt = {"language", "timeout_seconds"}
            unknown_opt = set(options.keys()) - allowed_opt
            if unknown_opt:
                errors.append(f"options contains unknown keys: {sorted(unknown_opt)}")
            language = options.get("language")
            if language is not None and language not in _ALLOWED_LANGUAGES:
                errors.append("options.language invalid")
            timeout = options.get("timeout_seconds")
            if timeout is not None:
                if not isinstance(timeout, (int, float)):
                    errors.append("options.timeout_seconds must be number")
                elif not (float(timeout) > 0 and float(timeout) <= 60):
                    errors.append("options.timeout_seconds out of range")

    return errors


def validate_success_response(payload: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["payload must be object"]

    if payload.get("ok") is not True:
        errors.append("ok must be true")
    if not _is_version(payload.get("api_version")):
        errors.append("api_version invalid")
    if not _is_request_id_like(payload.get("request_id")):
        errors.append("request_id invalid")

    result = payload.get("result")
    if not isinstance(result, dict):
        errors.append("result must be object")
        return errors

    required_result = {
        "entity_id",
        "input_mode",
        "as_of",
        "confidence",
        "building_profile",
        "context_profile",
        "suitability_light",
        "explainability",
    }
    missing = required_result - set(result.keys())
    if missing:
        errors.append(f"result missing keys: {sorted(missing)}")

    if not _is_non_empty_str(result.get("entity_id")):
        errors.append("result.entity_id invalid")
    if result.get("input_mode") not in {"address", "point"}:
        errors.append("result.input_mode invalid")
    if not _is_non_empty_str(result.get("as_of")):
        errors.append("result.as_of invalid")

    confidence = result.get("confidence")
    if not isinstance(confidence, (int, float)):
        errors.append("result.confidence must be number")
    elif not (0 <= float(confidence) <= 1):
        errors.append("result.confidence out of range")

    explainability = result.get("explainability")
    if not isinstance(explainability, dict):
        errors.append("result.explainability must be object")
    else:
        sources = explainability.get("sources")
        if not isinstance(sources, list) or not sources:
            errors.append("result.explainability.sources must be non-empty array")
        else:
            for idx, source in enumerate(sources):
                if not isinstance(source, dict):
                    errors.append(f"sources[{idx}] must be object")
                    continue
                if not _is_non_empty_str(source.get("source")):
                    errors.append(f"sources[{idx}].source invalid")
                if not _is_non_empty_str(source.get("as_of")):
                    errors.append(f"sources[{idx}].as_of invalid")
                score = source.get("confidence")
                if not isinstance(score, (int, float)) or not (0 <= float(score) <= 1):
                    errors.append(f"sources[{idx}].confidence invalid")

        for bucket_name in ("base", "personalized"):
            bucket = explainability.get(bucket_name)
            if not isinstance(bucket, dict):
                errors.append(f"result.explainability.{bucket_name} must be object")
                continue

            factors = bucket.get("factors")
            if not isinstance(factors, list) or not factors:
                errors.append(
                    f"result.explainability.{bucket_name}.factors must be non-empty array"
                )
                continue

            for idx, factor in enumerate(factors):
                if not isinstance(factor, dict):
                    errors.append(f"{bucket_name}.factors[{idx}] must be object")
                    continue

                if not _is_non_empty_str(factor.get("key")):
                    errors.append(f"{bucket_name}.factors[{idx}].key invalid")
                if not isinstance(factor.get("raw_value"), (int, float)):
                    errors.append(f"{bucket_name}.factors[{idx}].raw_value invalid")
                if not isinstance(factor.get("normalized"), (int, float)):
                    errors.append(f"{bucket_name}.factors[{idx}].normalized invalid")
                if not isinstance(factor.get("weight"), (int, float)):
                    errors.append(f"{bucket_name}.factors[{idx}].weight invalid")
                if not isinstance(factor.get("contribution"), (int, float)):
                    errors.append(f"{bucket_name}.factors[{idx}].contribution invalid")

                direction = factor.get("direction")
                if direction not in _ALLOWED_EXPLAINABILITY_DIRECTIONS:
                    errors.append(f"{bucket_name}.factors[{idx}].direction invalid")

                if not _is_non_empty_str(factor.get("reason")):
                    errors.append(f"{bucket_name}.factors[{idx}].reason invalid")
                if not _is_non_empty_str(factor.get("source")):
                    errors.append(f"{bucket_name}.factors[{idx}].source invalid")

    return errors


def validate_error_response(payload: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["payload must be object"]

    if payload.get("ok") is not False:
        errors.append("ok must be false")
    if not _is_version(payload.get("api_version")):
        errors.append("api_version invalid")
    if not _is_request_id_like(payload.get("request_id")):
        errors.append("request_id invalid")

    error = payload.get("error")
    if not isinstance(error, dict):
        errors.append("error must be object")
        return errors

    code = error.get("code")
    if code not in _ALLOWED_ERROR_CODES:
        errors.append("error.code invalid")
    if not _is_non_empty_str(error.get("message")):
        errors.append("error.message invalid")

    details = error.get("details")
    if details is not None:
        if not isinstance(details, list):
            errors.append("error.details must be array")
        else:
            for idx, row in enumerate(details):
                if not isinstance(row, dict):
                    errors.append(f"error.details[{idx}] must be object")
                    continue
                if not _is_non_empty_str(row.get("field")):
                    errors.append(f"error.details[{idx}].field invalid")
                if not _is_non_empty_str(row.get("issue")):
                    errors.append(f"error.details[{idx}].issue invalid")

    return errors


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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
            "## 6) CI-Check (verdrahtet)",
            "## 7) Scope-Abgrenzung BL-20.1.a / BL-20.1.b",
            "## 10) Stability Guide + Contract-Change-Policy (BL-20.1.d.wp4)",
            "docs/api/contract-stability-policy.md",
            "result.explainability.base.factors[*]",
            "result.explainability.personalized.factors[*]",
            "result.data.modules.explainability.base.factors[*]",
        ]
        for marker in markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in contract-v1.md: {marker}")

    def test_stability_policy_doc_contains_required_rules(self):
        self.assertTrue(STABILITY_POLICY_DOC.is_file(), msg="docs/api/contract-stability-policy.md fehlt")
        content = STABILITY_POLICY_DOC.read_text(encoding="utf-8")

        markers = [
            "Stabilitätsklassen (verbindlich)",
            "stable",
            "beta",
            "internal",
            "Non-Breaking",
            "Breaking",
            "CHANGELOG.md",
            "/api/v1",
            "scripts/validate_field_catalog.py",
        ]
        for marker in markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in contract-stability-policy.md: {marker}")

    def test_schema_files_exist_and_are_valid_json(self):
        schema_paths = [
            SCHEMA_DIR / "location-intelligence.request.schema.json",
            SCHEMA_DIR / "location-intelligence.response.schema.json",
            SCHEMA_DIR / "error.response.schema.json",
        ]

        for schema_path in schema_paths:
            self.assertTrue(schema_path.is_file(), msg=f"Schema fehlt: {schema_path}")
            payload = _read_json(schema_path)
            self.assertEqual(payload.get("type"), "object")
            self.assertIn("title", payload)
            self.assertIn("$schema", payload)

    def test_examples_validate_as_positive_cases(self):
        req_address = _read_json(EXAMPLE_DIR / "location-intelligence.request.address.json")
        req_point = _read_json(EXAMPLE_DIR / "location-intelligence.request.point.json")
        resp_ok = _read_json(EXAMPLE_DIR / "location-intelligence.response.success.address.json")
        resp_err = _read_json(EXAMPLE_DIR / "location-intelligence.response.error.bad-request.json")

        self.assertEqual(validate_request(req_address), [], msg="Example request(address) ungültig")
        self.assertEqual(validate_request(req_point), [], msg="Example request(point) ungültig")
        self.assertEqual(validate_success_response(resp_ok), [], msg="Example success response ungültig")
        self.assertEqual(validate_error_response(resp_err), [], msg="Example error response ungültig")

    def test_golden_positive_payloads(self):
        valid_dir = GOLDEN_DIR / "valid"
        self.assertTrue(valid_dir.is_dir(), msg="tests/data/api_contract_v1/valid fehlt")

        validators = {
            "request.": validate_request,
            "response.success.": validate_success_response,
            "response.error.": validate_error_response,
        }

        for payload_path in sorted(valid_dir.glob("*.json")):
            payload = _read_json(payload_path)
            validator = None
            for prefix, fn in validators.items():
                if payload_path.name.startswith(prefix):
                    validator = fn
                    break
            self.assertIsNotNone(validator, msg=f"Kein Validator für {payload_path.name}")
            errors = validator(payload)
            self.assertEqual(errors, [], msg=f"Valid-Golden-Case fehlgeschlagen ({payload_path.name}): {errors}")

    def test_golden_negative_payloads(self):
        invalid_dir = GOLDEN_DIR / "invalid"
        self.assertTrue(invalid_dir.is_dir(), msg="tests/data/api_contract_v1/invalid fehlt")

        validators = {
            "request.": validate_request,
            "response.success.": validate_success_response,
            "response.error.": validate_error_response,
        }

        for payload_path in sorted(invalid_dir.glob("*.json")):
            payload = _read_json(payload_path)
            validator = None
            for prefix, fn in validators.items():
                if payload_path.name.startswith(prefix):
                    validator = fn
                    break
            self.assertIsNotNone(validator, msg=f"Kein Validator für {payload_path.name}")
            errors = validator(payload)
            self.assertGreater(
                len(errors),
                0,
                msg=f"Invalid-Golden-Case wurde fälschlich akzeptiert: {payload_path.name}",
            )


if __name__ == "__main__":
    unittest.main()
