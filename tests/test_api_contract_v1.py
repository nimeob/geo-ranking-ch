import json
import math
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
_ALLOWED_PREFERENCE_ENUMS = {
    "lifestyle_density": {"rural", "suburban", "urban"},
    "noise_tolerance": {"low", "medium", "high"},
    "nightlife_preference": {"avoid", "neutral", "prefer"},
    "school_proximity": {"avoid", "neutral", "prefer"},
    "family_friendly_focus": {"low", "medium", "high"},
    "commute_priority": {"car", "pt", "bike", "mixed"},
}


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

    allowed_top = {"request_id", "input", "requested_modules", "preferences", "options"}
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
            allowed_opt = {"language", "timeout_seconds", "capabilities", "entitlements"}
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

            capabilities = options.get("capabilities")
            if capabilities is not None and not isinstance(capabilities, dict):
                errors.append("options.capabilities must be object")

            entitlements = options.get("entitlements")
            if entitlements is not None and not isinstance(entitlements, dict):
                errors.append("options.entitlements must be object")

    preferences = payload.get("preferences")
    if preferences is not None:
        if not isinstance(preferences, dict):
            errors.append("preferences must be object")
        else:
            allowed_pref = set(_ALLOWED_PREFERENCE_ENUMS) | {"weights"}
            unknown_pref = set(preferences.keys()) - allowed_pref
            if unknown_pref:
                errors.append(f"preferences contains unknown keys: {sorted(unknown_pref)}")

            for field_name, allowed_values in _ALLOWED_PREFERENCE_ENUMS.items():
                value = preferences.get(field_name)
                if value is None:
                    continue
                if value not in allowed_values:
                    errors.append(
                        f"preferences.{field_name} invalid (allowed={sorted(allowed_values)})"
                    )

            weights = preferences.get("weights")
            if weights is not None:
                if not isinstance(weights, dict):
                    errors.append("preferences.weights must be object")
                else:
                    unknown_weights = set(weights.keys()) - set(_ALLOWED_PREFERENCE_ENUMS)
                    if unknown_weights:
                        errors.append(
                            "preferences.weights contains unknown keys: "
                            f"{sorted(unknown_weights)}"
                        )
                    for key, weight in weights.items():
                        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
                            errors.append(f"preferences.weights.{key} must be finite number")
                            continue
                        weight_num = float(weight)
                        if not math.isfinite(weight_num):
                            errors.append(f"preferences.weights.{key} must be finite number")
                            continue
                        if not (0 <= weight_num <= 1):
                            errors.append(f"preferences.weights.{key} out of range")

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

    suitability = result.get("suitability_light")
    if not isinstance(suitability, dict):
        errors.append("result.suitability_light must be object")
    else:
        for field_name in ("score", "base_score", "personalized_score"):
            value = suitability.get(field_name)
            if not isinstance(value, (int, float)):
                errors.append(f"result.suitability_light.{field_name} must be number")
                continue
            if not (0 <= float(value) <= 100):
                errors.append(f"result.suitability_light.{field_name} out of range")

        if suitability.get("traffic_light") not in {"green", "yellow", "red"}:
            errors.append("result.suitability_light.traffic_light invalid")

    status = result.get("status")
    if status is not None:
        if not isinstance(status, dict):
            errors.append("result.status must be object")
        else:
            capabilities = status.get("capabilities")
            if capabilities is not None and not isinstance(capabilities, dict):
                errors.append("result.status.capabilities must be object")

            entitlements = status.get("entitlements")
            if entitlements is not None and not isinstance(entitlements, dict):
                errors.append("result.status.entitlements must be object")

            personalization = status.get("personalization")
            if personalization is not None:
                if not isinstance(personalization, dict):
                    errors.append("result.status.personalization must be object")
                else:
                    if personalization.get("state") not in {"active", "partial", "deactivated"}:
                        errors.append("result.status.personalization.state invalid")
                    source = personalization.get("source")
                    if source is not None and not _is_non_empty_str(source):
                        errors.append("result.status.personalization.source invalid")
                    fallback_applied = personalization.get("fallback_applied")
                    if fallback_applied is not None and not isinstance(fallback_applied, bool):
                        errors.append("result.status.personalization.fallback_applied must be boolean")
                    signal_strength = personalization.get("signal_strength")
                    if signal_strength is not None:
                        if isinstance(signal_strength, bool) or not isinstance(signal_strength, (int, float)):
                            errors.append("result.status.personalization.signal_strength must be number")
                        elif not math.isfinite(float(signal_strength)) or float(signal_strength) < 0:
                            errors.append("result.status.personalization.signal_strength out of range")

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
            "## 14) BL-20.1.h Capability-/Entitlement-Envelope (BL-30-ready)",
            "options.capabilities",
            "result.status.entitlements",
            "result.status.personalization",
            "#105",
            "#106",
            "#107",
            "#18",
            "BL-20.4.c Preference-Profile Envelope",
            "preferences.weights",
            "lifestyle_density",
            "commute_priority",
            "BL-20.4.d.wp2 Zweistufige Suitability-Score-Felder",
            "result.suitability_light.base_score",
            "result.suitability_light.personalized_score",
            "BL-20.1.k.wp1 Contract: Code-only Response + Dictionary-Referenzfelder",
            "result.status.dictionary.version",
            "result.status.dictionary.etag",
            "analyze.response.grouped.code-only-before.json",
            "analyze.response.grouped.code-only-after.json",
            "BL-20.1.k.wp2 Dictionary-Endpoints (versioniert + cachebar)",
            "GET /api/v1/dictionaries",
            "If-None-Match",
            "304 Not Modified",
            "#286",
            "#287",
            "#288",
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
            "BL-20.1.h Capability-/Entitlement-Envelope",
            "result.status.capabilities",
            "options.entitlements",
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

    def test_response_schemas_define_dictionary_envelope_contract(self):
        grouped_schema = _read_json(SCHEMA_DIR / "analyze.grouped.response.schema.json")
        legacy_schema = _read_json(SCHEMA_DIR / "location-intelligence.response.schema.json")

        for schema_name, schema_payload in (
            ("grouped", grouped_schema),
            ("legacy", legacy_schema),
        ):
            dictionary = (
                schema_payload["properties"]["result"]["properties"]["status"]["properties"].get("dictionary")
            )
            self.assertIsInstance(dictionary, dict, msg=f"dictionary-Envelope fehlt im {schema_name}-Schema")
            self.assertEqual(
                set(dictionary.get("required", [])),
                {"version", "etag"},
                msg=f"dictionary.required im {schema_name}-Schema muss version+etag erzwingen",
            )
            self.assertEqual(dictionary.get("type"), "object")
            self.assertFalse(dictionary.get("additionalProperties", True))

            domains = dictionary.get("properties", {}).get("domains")
            self.assertIsInstance(domains, dict, msg=f"dictionary.domains fehlt im {schema_name}-Schema")
            domain_item = domains.get("additionalProperties", {})
            self.assertEqual(
                set(domain_item.get("required", [])),
                {"version", "etag"},
                msg=f"dictionary.domains[*] muss im {schema_name}-Schema version+etag erzwingen",
            )

    def test_code_only_before_after_examples_capture_contract_diff(self):
        before = _read_json(
            REPO_ROOT
            / "docs"
            / "api"
            / "examples"
            / "current"
            / "analyze.response.grouped.code-only-before.json"
        )
        after = _read_json(
            REPO_ROOT
            / "docs"
            / "api"
            / "examples"
            / "current"
            / "analyze.response.grouped.code-only-after.json"
        )

        self.assertEqual(before.get("request_id"), after.get("request_id"))
        self.assertNotIn("dictionary", before["result"]["status"])
        self.assertIn("dictionary", after["result"]["status"])

        after_dictionary = after["result"]["status"]["dictionary"]
        self.assertIn("version", after_dictionary)
        self.assertIn("etag", after_dictionary)
        self.assertIn("domains", after_dictionary)

    def test_examples_validate_as_positive_cases(self):
        req_address = _read_json(EXAMPLE_DIR / "location-intelligence.request.address.json")
        req_point = _read_json(EXAMPLE_DIR / "location-intelligence.request.point.json")
        resp_ok = _read_json(EXAMPLE_DIR / "location-intelligence.response.success.address.json")
        resp_err = _read_json(EXAMPLE_DIR / "location-intelligence.response.error.bad-request.json")

        self.assertEqual(validate_request(req_address), [], msg="Example request(address) ungültig")
        self.assertEqual(validate_request(req_point), [], msg="Example request(point) ungültig")
        self.assertEqual(validate_success_response(resp_ok), [], msg="Example success response ungültig")
        self.assertEqual(validate_error_response(resp_err), [], msg="Example error response ungültig")

    def test_capability_entitlement_envelope_is_additive_for_legacy_clients(self):
        req_baseline = _read_json(GOLDEN_DIR / "valid" / "request.address.minimal.json")
        req_with_meta = json.loads(json.dumps(req_baseline))
        req_with_meta["options"] = {
            "capabilities": {
                "deep_mode": {"state": "beta", "requested": False},
                "future_module_x": {"state": "internal", "requested": True},
            },
            "entitlements": {
                "plan": "starter",
                "status": "active",
                "origin": "contract-test",
            },
        }

        self.assertEqual(validate_request(req_baseline), [], msg="Baseline-Request muss valide bleiben")
        self.assertEqual(
            validate_request(req_with_meta),
            [],
            msg="Capability-/Entitlement-Envelope muss additiv und valide sein",
        )

        resp_baseline = _read_json(GOLDEN_DIR / "valid" / "response.success.minimal.json")
        resp_with_meta = json.loads(json.dumps(resp_baseline))
        resp_with_meta["result"]["status"] = {
            "capabilities": {
                "deep_mode": {"state": "beta", "available": False},
                "pricing_preview": {"state": "internal", "available": False},
            },
            "entitlements": {
                "plan": {"state": "stable", "value": "starter"},
                "limits": {
                    "state": "beta",
                    "requests_per_day": 500,
                },
            },
            "personalization": {
                "state": "partial",
                "source": "base_score_fallback",
                "fallback_applied": True,
                "signal_strength": 0.0,
            },
        }

        self.assertEqual(validate_success_response(resp_baseline), [], msg="Baseline-Response muss valide bleiben")
        self.assertEqual(
            validate_success_response(resp_with_meta),
            [],
            msg="Additive status.capabilities/status.entitlements/status.personalization dürfen Legacy-Response nicht brechen",
        )

        baseline_projection = {
            key: resp_baseline["result"][key]
            for key in ("entity_id", "input_mode", "as_of", "confidence")
        }
        additive_projection = {
            key: resp_with_meta["result"][key]
            for key in ("entity_id", "input_mode", "as_of", "confidence")
        }
        self.assertEqual(
            additive_projection,
            baseline_projection,
            msg="Legacy-Projektion muss trotz Capability-/Entitlement-Meta unverändert bleiben",
        )

    def test_preference_profile_is_additive_with_defined_defaults(self):
        req_baseline = _read_json(GOLDEN_DIR / "valid" / "request.address.minimal.json")
        req_with_preferences = json.loads(json.dumps(req_baseline))
        req_with_preferences["preferences"] = {
            "lifestyle_density": "urban",
            "noise_tolerance": "low",
            "nightlife_preference": "prefer",
            "school_proximity": "neutral",
            "family_friendly_focus": "medium",
            "commute_priority": "pt",
            "weights": {
                "noise_tolerance": 0.8,
                "commute_priority": 0.7,
            },
        }

        req_with_partial_preferences = json.loads(json.dumps(req_baseline))
        req_with_partial_preferences["preferences"] = {
            "lifestyle_density": "rural",
            "weights": {"school_proximity": 0.6},
        }

        self.assertEqual(validate_request(req_baseline), [], msg="Baseline-Request muss valide bleiben")
        self.assertEqual(
            validate_request(req_with_preferences),
            [],
            msg="Vollständiges Preference-Profil muss als additive Erweiterung valide sein",
        )
        self.assertEqual(
            validate_request(req_with_partial_preferences),
            [],
            msg="Partielle Preference-Profile müssen valide sein (Defaults greifen implizit)",
        )

    def test_invalid_preference_weights_are_rejected_by_contract_validator(self):
        req_baseline = _read_json(GOLDEN_DIR / "valid" / "request.address.minimal.json")

        invalid_weights = [
            ("string", "0.5", "must be finite number"),
            ("bool", True, "must be finite number"),
            ("nan", float("nan"), "must be finite number"),
            ("inf", float("inf"), "must be finite number"),
            ("negative", -0.1, "out of range"),
            ("gt_one", 1.1, "out of range"),
        ]

        for case_name, value, expected in invalid_weights:
            with self.subTest(case=case_name):
                payload = json.loads(json.dumps(req_baseline))
                payload["preferences"] = {
                    "lifestyle_density": "urban",
                    "weights": {
                        "noise_tolerance": value,
                    },
                }
                errors = validate_request(payload)
                self.assertTrue(errors, msg=f"Erwarteter Vertragsfehler fehlt für {case_name}")
                self.assertTrue(
                    any(expected in err for err in errors),
                    msg=f"Unerwartete Fehler für {case_name}: {errors}",
                )

    def test_two_stage_suitability_scores_are_explicit_in_success_response(self):
        resp_baseline = _read_json(GOLDEN_DIR / "valid" / "response.success.minimal.json")
        suitability = resp_baseline.get("result", {}).get("suitability_light", {})

        self.assertIn("base_score", suitability)
        self.assertIn("personalized_score", suitability)
        self.assertEqual(
            suitability.get("base_score"),
            suitability.get("personalized_score"),
            msg="Ohne Präferenzkontext muss fallback-konform personalized_score==base_score sein",
        )

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
