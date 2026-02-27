import json
import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from urllib import error, request


REPO_ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _http_json(
    method: str,
    url: str,
    payload=None,
    headers=None,
    timeout: float = 10.0,
    *,
    return_headers: bool = False,
):
    data = None
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = request.Request(url, method=method, data=data, headers=req_headers)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            parsed = json.loads(body)
            if return_headers:
                return (
                    resp.status,
                    parsed,
                    {k.lower(): v for k, v in resp.headers.items()},
                )
            return resp.status, parsed
    except error.HTTPError as e:
        body = e.read().decode("utf-8")
        parsed = json.loads(body) if body else {}
        if return_headers:
            header_map = {
                k.lower(): v for k, v in (e.headers.items() if e.headers else [])
            }
            return e.code, parsed, header_map
        return e.code, parsed


def _http_raw_json(
    method: str,
    url: str,
    raw_body: bytes,
    headers=None,
    timeout: float = 10.0,
):
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = request.Request(url, method=method, data=raw_body, headers=req_headers)

    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body)
    except error.HTTPError as e:
        body = e.read().decode("utf-8")
        parsed = json.loads(body) if body else {}
        return e.code, parsed


def _collect_status_like_paths(payload, prefix=""):
    paths = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_str = str(key)
            current = f"{prefix}.{key_str}" if prefix else key_str
            normalized = key_str.lower()
            if (
                normalized == "status"
                or normalized.startswith("status_")
                or normalized.endswith("_status")
            ):
                paths.append(current)
            paths.extend(_collect_status_like_paths(value, current))
    elif isinstance(payload, list):
        for idx, item in enumerate(payload):
            current = f"{prefix}[{idx}]" if prefix else f"[{idx}]"
            paths.extend(_collect_status_like_paths(item, current))
    return paths


class TestWebServiceE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        env = os.environ.copy()
        env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.port),
                "API_AUTH_TOKEN": "bl18-token",
                # klein halten, damit fehlerhafte Werte schneller sichtbar sind
                "ANALYZE_DEFAULT_TIMEOUT_SECONDS": "3",
                "ANALYZE_MAX_TIMEOUT_SECONDS": "10",
                "PYTHONPATH": str(REPO_ROOT),
                "ENABLE_E2E_FAULT_INJECTION": "1",
            }
        )
        cls.proc = subprocess.Popen(
            [sys.executable, "-m", "src.web_service"],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.time() + 12
        while time.time() < deadline:
            try:
                status, _ = _http_json("GET", f"{cls.base_url}/health", payload=None)
                if status == 200:
                    return
            except Exception:
                pass
            time.sleep(0.2)

        raise RuntimeError("web_service wurde lokal nicht rechtzeitig erreichbar")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.proc.kill()

    def test_health_and_version(self):
        status, health = _http_json("GET", f"{self.base_url}/health")
        self.assertEqual(status, 200)
        self.assertTrue(health.get("ok"))

        status, version = _http_json("GET", f"{self.base_url}/version")
        self.assertEqual(status, 200)
        self.assertIn("version", version)

    def test_health_and_version_accept_trailing_slash_and_query(self):
        status, health = _http_json("GET", f"{self.base_url}/health/?probe=1")
        self.assertEqual(status, 200)
        self.assertTrue(health.get("ok"))

        status, version = _http_json("GET", f"{self.base_url}/version/?ts=1")
        self.assertEqual(status, 200)
        self.assertIn("version", version)

    def test_health_and_version_accept_double_slashes(self):
        status, health = _http_json("GET", f"{self.base_url}//health//?probe=1")
        self.assertEqual(status, 200)
        self.assertTrue(health.get("ok"))

        status, version = _http_json("GET", f"{self.base_url}//version///?ts=1")
        self.assertEqual(status, 200)
        self.assertIn("version", version)

    def test_not_found(self):
        status, body = _http_json("GET", f"{self.base_url}/missing")
        self.assertEqual(status, 404)
        self.assertEqual(body.get("error"), "not_found")

    def test_auth_required_for_analyze(self):
        status, body = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={"query": "Bahnhofstrasse 1, 8001 Zürich"},
        )
        self.assertEqual(status, 401)
        self.assertEqual(body.get("error"), "unauthorized")

    def test_auth_accepts_case_insensitive_bearer_and_trimmed_whitespace(self):
        for header_value in (
            "bearer bl18-token",
            "  BeArEr    bl18-token  ",
        ):
            with self.subTest(header_value=header_value):
                status, body = _http_json(
                    "POST",
                    f"{self.base_url}/analyze",
                    payload={"query": "__ok__", "timeout_seconds": 2},
                    headers={"Authorization": header_value},
                )
                self.assertEqual(status, 200)
                self.assertTrue(body.get("ok"))

    def test_auth_rejects_malformed_bearer_headers(self):
        for header_value in (
            "Bearer",
            "Bearer bl18-token extra",
            "Basic bl18-token",
        ):
            with self.subTest(header_value=header_value):
                status, body = _http_json(
                    "POST",
                    f"{self.base_url}/analyze",
                    payload={"query": "__ok__", "timeout_seconds": 2},
                    headers={"Authorization": header_value},
                )
                self.assertEqual(status, 401)
                self.assertEqual(body.get("error"), "unauthorized")

    def test_analyze_happy_path(self):
        status, body = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={
                "query": "__ok__",
                "intelligence_mode": "basic",
                "timeout_seconds": 2,
            },
            headers={"Authorization": "Bearer bl18-token"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(body.get("ok"))
        result = body.get("result")
        self.assertIsInstance(result, dict)
        self.assertIn("status", result)
        self.assertIn("data", result)

        status_block = result.get("status")
        self.assertIsInstance(status_block, dict)
        self.assertIn("quality", status_block)
        self.assertIn("source_health", status_block)
        self.assertIn("source_meta", status_block)

        data_block = result.get("data")
        self.assertIsInstance(data_block, dict)
        self.assertIn("entity", data_block)
        self.assertIn("modules", data_block)
        self.assertIn("by_source", data_block)

        status_like_paths = _collect_status_like_paths(data_block)
        self.assertEqual(
            status_like_paths,
            [],
            msg=f"status-Felder dürfen in result.data nicht vorkommen: {status_like_paths}",
        )

    def test_analyze_accepts_trailing_slash_and_query(self):
        request_id = "bl18-e2e-analyze-query-path"
        status, body, resp_headers = _http_json(
            "POST",
            f"{self.base_url}/analyze/?trace=1",
            payload={
                "query": "__ok__",
                "intelligence_mode": "basic",
                "timeout_seconds": 2,
            },
            headers={
                "Authorization": "Bearer bl18-token",
                "X-Request-Id": request_id,
            },
            return_headers=True,
        )
        self.assertEqual(status, 200)
        self.assertTrue(body.get("ok"))
        self.assertEqual(body.get("request_id"), request_id)
        self.assertEqual(resp_headers.get("x-request-id"), request_id)

    def test_analyze_accepts_double_slashes_and_query(self):
        request_id = "bl18-e2e-analyze-double-slash-path"
        status, body, resp_headers = _http_json(
            "POST",
            f"{self.base_url}//analyze//?trace=double-slash",
            payload={
                "query": "__ok__",
                "intelligence_mode": "basic",
                "timeout_seconds": 2,
            },
            headers={
                "Authorization": "Bearer bl18-token",
                "X-Request-Id": request_id,
            },
            return_headers=True,
        )
        self.assertEqual(status, 200)
        self.assertTrue(body.get("ok"))
        self.assertEqual(body.get("request_id"), request_id)
        self.assertEqual(resp_headers.get("x-request-id"), request_id)

    def test_analyze_accepts_case_insensitive_mode_with_whitespace(self):
        status, body = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={
                "query": "__ok__",
                "intelligence_mode": "  ExTenDeD  ",
                "timeout_seconds": 2,
            },
            headers={"Authorization": "Bearer bl18-token"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(body.get("ok"))
        self.assertIn("result", body)

    def test_analyze_ignores_unknown_options_keys_as_additive_noop(self):
        status, body = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={
                "query": "__ok__",
                "intelligence_mode": "basic",
                "timeout_seconds": 2,
                "options": {
                    "future_flag": True,
                    "deep_mode": {"enabled": True, "profile": "pro"},
                    "nested_future": {"alpha": {"beta": 1}},
                },
            },
            headers={"Authorization": "Bearer bl18-token"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(body.get("ok"))
        self.assertIn("result", body)

    def test_bad_request_options_must_be_object_when_provided(self):
        invalid_options = (
            [],
            "deep",
            1,
            True,
        )
        for value in invalid_options:
            with self.subTest(options=value):
                status, body = _http_json(
                    "POST",
                    f"{self.base_url}/analyze",
                    payload={
                        "query": "__ok__",
                        "intelligence_mode": "basic",
                        "timeout_seconds": 2,
                        "options": value,
                    },
                    headers={"Authorization": "Bearer bl18-token"},
                )
                self.assertEqual(status, 400)
                self.assertEqual(body.get("error"), "bad_request")
                self.assertIn("options must be an object", body.get("message", ""))

    def test_analyze_accepts_valid_preferences_profile(self):
        status, body = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={
                "query": "__ok__",
                "intelligence_mode": "basic",
                "timeout_seconds": 2,
                "preferences": {
                    "lifestyle_density": "urban",
                    "noise_tolerance": "low",
                    "nightlife_preference": "prefer",
                    "school_proximity": "avoid",
                    "family_friendly_focus": "medium",
                    "commute_priority": "pt",
                    "weights": {
                        "noise_tolerance": 0.8,
                        "nightlife_preference": 0.4,
                        "commute_priority": 1,
                    },
                },
            },
            headers={"Authorization": "Bearer bl18-token"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(body.get("ok"))
        self.assertIn("result", body)

    def test_bad_request_preferences_must_be_object_when_provided(self):
        invalid_preferences = (
            [],
            "urban",
            1,
            True,
        )
        for value in invalid_preferences:
            with self.subTest(preferences=value):
                status, body = _http_json(
                    "POST",
                    f"{self.base_url}/analyze",
                    payload={
                        "query": "__ok__",
                        "intelligence_mode": "basic",
                        "timeout_seconds": 2,
                        "preferences": value,
                    },
                    headers={"Authorization": "Bearer bl18-token"},
                )
                self.assertEqual(status, 400)
                self.assertEqual(body.get("error"), "bad_request")
                self.assertIn("preferences must be an object", body.get("message", ""))

    def test_bad_request_preferences_reject_invalid_enums_and_weights(self):
        invalid_cases = [
            (
                "invalid_enum",
                {"preferences": {"lifestyle_density": "village"}},
                "preferences.lifestyle_density",
            ),
            (
                "unknown_dimension",
                {"preferences": {"sunshine_focus": "high"}},
                "preferences contains unknown keys",
            ),
            (
                "weights_not_object",
                {"preferences": {"weights": "high"}},
                "preferences.weights must be an object",
            ),
            (
                "weights_unknown_key",
                {"preferences": {"weights": {"sunshine_focus": 0.6}}},
                "preferences.weights contains unknown keys",
            ),
            (
                "weights_out_of_range",
                {"preferences": {"weights": {"noise_tolerance": 1.5}}},
                "preferences.weights.noise_tolerance must be between 0 and 1",
            ),
        ]

        for case_name, patch_payload, expected_message in invalid_cases:
            with self.subTest(case=case_name):
                payload = {
                    "query": "__ok__",
                    "intelligence_mode": "basic",
                    "timeout_seconds": 2,
                }
                payload.update(patch_payload)
                status, body = _http_json(
                    "POST",
                    f"{self.base_url}/analyze",
                    payload=payload,
                    headers={"Authorization": "Bearer bl18-token"},
                )
                self.assertEqual(status, 400)
                self.assertEqual(body.get("error"), "bad_request")
                self.assertIn(expected_message, body.get("message", ""))

    def test_bad_request_invalid_mode(self):
        status, body = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={
                "query": "Bahnhofstrasse 1, 8001 Zürich",
                "intelligence_mode": "future-mode",
            },
            headers={"Authorization": "Bearer bl18-token"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(body.get("error"), "bad_request")

    def test_bad_request_non_finite_timeout(self):
        status, body = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={
                "query": "Bahnhofstrasse 1, 8001 Zürich",
                "timeout_seconds": "nan",
            },
            headers={"Authorization": "Bearer bl18-token"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(body.get("error"), "bad_request")
        self.assertIn("timeout_seconds", body.get("message", ""))

    def test_bad_request_empty_body(self):
        status, body = _http_raw_json(
            "POST",
            f"{self.base_url}/analyze",
            raw_body=b"",
            headers={"Authorization": "Bearer bl18-token"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(body.get("error"), "bad_request")

    def test_bad_request_invalid_json_and_body_edgecases(self):
        cases = [
            (
                "malformed_json_trailing_comma",
                b'{"query":"__ok__",}',
                None,
            ),
            (
                "invalid_utf8_json",
                b'{"query":"__ok__"}\x80',
                "body must be valid utf-8 json",
            ),
            (
                "json_array_instead_of_object",
                b'["__ok__"]',
                "json body must be an object",
            ),
            (
                "json_string_instead_of_object",
                b'"__ok__"',
                "json body must be an object",
            ),
        ]

        for name, raw_body, expected_message in cases:
            with self.subTest(case=name):
                status, body = _http_raw_json(
                    "POST",
                    f"{self.base_url}/analyze",
                    raw_body=raw_body,
                    headers={"Authorization": "Bearer bl18-token"},
                )
                self.assertEqual(status, 400)
                self.assertEqual(body.get("error"), "bad_request")
                self.assertIn("request_id", body)
                if expected_message:
                    self.assertIn(expected_message, body.get("message", ""))

    def test_timeout_and_internal_are_mapped(self):
        status, body = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={"query": "__timeout__"},
            headers={"Authorization": "Bearer bl18-token"},
        )
        self.assertEqual(status, 504)
        self.assertEqual(body.get("error"), "timeout")

        status, body = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={"query": "__internal__"},
            headers={"Authorization": "Bearer bl18-token"},
        )
        self.assertEqual(status, 500)
        self.assertEqual(body.get("error"), "internal")

    def test_request_id_echoed_for_analyze_paths(self):
        request_id = "bl18-e2e-request-id"

        status, body, resp_headers = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={"query": "__ok__", "timeout_seconds": 2},
            headers={
                "Authorization": "Bearer bl18-token",
                "X-Request-Id": request_id,
            },
            return_headers=True,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body.get("request_id"), request_id)
        self.assertEqual(resp_headers.get("x-request-id"), request_id)

        status, body, resp_headers = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={"query": "__ok__", "timeout_seconds": 2},
            headers={"X-Request-Id": request_id},
            return_headers=True,
        )
        self.assertEqual(status, 401)
        self.assertEqual(body.get("error"), "unauthorized")
        self.assertEqual(body.get("request_id"), request_id)
        self.assertEqual(resp_headers.get("x-request-id"), request_id)

    def test_request_id_falls_back_to_correlation_header_when_primary_is_blank(self):
        correlation_id = "bl18-e2e-correlation-id"
        status, body, resp_headers = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={"query": "__ok__", "timeout_seconds": 2},
            headers={
                "Authorization": "Bearer bl18-token",
                "X-Request-Id": "   ",
                "X-Correlation-Id": correlation_id,
            },
            return_headers=True,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body.get("request_id"), correlation_id)
        self.assertEqual(resp_headers.get("x-request-id"), correlation_id)

    def test_request_id_falls_back_to_correlation_header_when_primary_contains_control_chars(self):
        correlation_id = "bl18-e2e-correlation-control-fallback"
        status, body, resp_headers = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={"query": "__ok__", "timeout_seconds": 2},
            headers={
                "Authorization": "Bearer bl18-token",
                "X-Request-Id": "bl18\tbad-id",
                "X-Correlation-Id": correlation_id,
            },
            return_headers=True,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body.get("request_id"), correlation_id)
        self.assertEqual(resp_headers.get("x-request-id"), correlation_id)

    def test_request_id_falls_back_to_correlation_header_when_primary_contains_embedded_whitespace(self):
        correlation_id = "bl18-e2e-correlation-whitespace-fallback"
        status, body, resp_headers = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={"query": "__ok__", "timeout_seconds": 2},
            headers={
                "Authorization": "Bearer bl18-token",
                "X-Request-Id": "bl18 bad-id",
                "X-Correlation-Id": correlation_id,
            },
            return_headers=True,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body.get("request_id"), correlation_id)
        self.assertEqual(resp_headers.get("x-request-id"), correlation_id)

    def test_request_id_falls_back_to_correlation_header_when_primary_contains_delimiters(self):
        correlation_id = "bl18-e2e-correlation-delimiter-fallback"
        status, body, resp_headers = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={"query": "__ok__", "timeout_seconds": 2},
            headers={
                "Authorization": "Bearer bl18-token",
                "X-Request-Id": "bl18,bad-id",
                "X-Correlation-Id": correlation_id,
            },
            return_headers=True,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body.get("request_id"), correlation_id)
        self.assertEqual(resp_headers.get("x-request-id"), correlation_id)

    def test_request_id_falls_back_to_correlation_header_when_primary_is_too_long(self):
        correlation_id = "bl18-e2e-correlation-length-fallback"
        too_long = "x" * 129
        status, body, resp_headers = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={"query": "__ok__", "timeout_seconds": 2},
            headers={
                "Authorization": "Bearer bl18-token",
                "X-Request-Id": too_long,
                "X-Correlation-Id": correlation_id,
            },
            return_headers=True,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body.get("request_id"), correlation_id)
        self.assertEqual(resp_headers.get("x-request-id"), correlation_id)

    def test_request_id_falls_back_to_correlation_header_when_primary_contains_non_ascii(self):
        correlation_id = "bl18-e2e-correlation-nonascii-fallback"
        status, body, resp_headers = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={"query": "__ok__", "timeout_seconds": 2},
            headers={
                "Authorization": "Bearer bl18-token",
                "X-Request-Id": "bl18-é-bad-id",
                "X-Correlation-Id": correlation_id,
            },
            return_headers=True,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body.get("request_id"), correlation_id)
        self.assertEqual(resp_headers.get("x-request-id"), correlation_id)

    def test_request_id_accepts_underscore_primary_header(self):
        request_id = "bl18-e2e-underscore-request-id"
        status, body, resp_headers = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={"query": "__ok__", "timeout_seconds": 2},
            headers={
                "Authorization": "Bearer bl18-token",
                "X_Request_Id": request_id,
            },
            return_headers=True,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body.get("request_id"), request_id)
        self.assertEqual(resp_headers.get("x-request-id"), request_id)

    def test_request_id_accepts_lowercase_underscore_primary_header_alias(self):
        request_id = "bl18-e2e-lowercase-underscore-request-id"
        status, body, resp_headers = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={"query": "__ok__", "timeout_seconds": 2},
            headers={
                "Authorization": "Bearer bl18-token",
                "x_request_id": request_id,
            },
            return_headers=True,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body.get("request_id"), request_id)
        self.assertEqual(resp_headers.get("x-request-id"), request_id)

    def test_request_id_prefers_valid_underscore_primary_when_hyphen_primary_is_invalid(self):
        underscore_request_id = "bl18-e2e-underscore-primary-fallback"
        status, body, resp_headers = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={"query": "__ok__", "timeout_seconds": 2},
            headers={
                "Authorization": "Bearer bl18-token",
                "X-Request-Id": "bl18 bad-id",
                "X_Request_Id": underscore_request_id,
                "X-Correlation-Id": "bl18-e2e-correlation-should-not-win",
            },
            return_headers=True,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body.get("request_id"), underscore_request_id)
        self.assertEqual(resp_headers.get("x-request-id"), underscore_request_id)

    def test_request_id_falls_back_to_correlation_when_underscore_primary_is_invalid(self):
        correlation_id = "bl18-e2e-correlation-after-invalid-underscore-primary"
        status, body, resp_headers = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={"query": "__ok__", "timeout_seconds": 2},
            headers={
                "Authorization": "Bearer bl18-token",
                "X-Request-Id": "bl18 bad-id",
                "X_Request_Id": "bl18\tunderscore-bad-id",
                "X-Correlation-Id": correlation_id,
            },
            return_headers=True,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body.get("request_id"), correlation_id)
        self.assertEqual(resp_headers.get("x-request-id"), correlation_id)

    def test_request_id_falls_back_to_underscore_correlation_header(self):
        correlation_id = "bl18-e2e-underscore-correlation-id"
        status, body, resp_headers = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={"query": "__ok__", "timeout_seconds": 2},
            headers={
                "Authorization": "Bearer bl18-token",
                "X-Request-Id": "bl18 bad-id",
                "X_Correlation_Id": correlation_id,
            },
            return_headers=True,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body.get("request_id"), correlation_id)
        self.assertEqual(resp_headers.get("x-request-id"), correlation_id)

    def test_request_id_accepts_short_primary_header_alias(self):
        request_id = "bl18-e2e-short-primary-request-id"
        status, body, resp_headers = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={"query": "__ok__", "timeout_seconds": 2},
            headers={
                "Authorization": "Bearer bl18-token",
                "Request-Id": request_id,
            },
            return_headers=True,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body.get("request_id"), request_id)
        self.assertEqual(resp_headers.get("x-request-id"), request_id)

    def test_request_id_accepts_short_primary_underscore_header_alias(self):
        request_id = "bl18-e2e-short-underscore-primary-request-id"
        status, body, resp_headers = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={"query": "__ok__", "timeout_seconds": 2},
            headers={
                "Authorization": "Bearer bl18-token",
                "Request_Id": request_id,
            },
            return_headers=True,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body.get("request_id"), request_id)
        self.assertEqual(resp_headers.get("x-request-id"), request_id)

    def test_request_id_falls_back_to_short_correlation_alias(self):
        correlation_id = "bl18-e2e-short-correlation-fallback"
        status, body, resp_headers = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={"query": "__ok__", "timeout_seconds": 2},
            headers={
                "Authorization": "Bearer bl18-token",
                "X-Request-Id": "bl18 bad-id",
                "Request-Id": "bl18,bad-short-request",
                "Correlation-Id": correlation_id,
            },
            return_headers=True,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body.get("request_id"), correlation_id)
        self.assertEqual(resp_headers.get("x-request-id"), correlation_id)

    def test_request_id_falls_back_to_short_underscore_correlation_alias(self):
        correlation_id = "bl18-e2e-short-underscore-correlation-fallback"
        status, body, resp_headers = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={"query": "__ok__", "timeout_seconds": 2},
            headers={
                "Authorization": "Bearer bl18-token",
                "X-Request-Id": "bl18 bad-id",
                "Request_Id": "bl18,bad-short-underscore-request",
                "Correlation_Id": correlation_id,
            },
            return_headers=True,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body.get("request_id"), correlation_id)
        self.assertEqual(resp_headers.get("x-request-id"), correlation_id)


class TestWebServiceEnvPortFallback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        env = os.environ.copy()
        env.update(
            {
                "HOST": "127.0.0.1",
                "WEB_PORT": str(cls.port),
                "PYTHONPATH": str(REPO_ROOT),
            }
        )
        env.pop("PORT", None)

        cls.proc = subprocess.Popen(
            [sys.executable, "-m", "src.web_service"],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        deadline = time.time() + 12
        while time.time() < deadline:
            try:
                status, _ = _http_json("GET", f"{cls.base_url}/health", payload=None)
                if status == 200:
                    return
            except Exception:
                pass
            time.sleep(0.2)

        raise RuntimeError("web_service wurde via WEB_PORT nicht rechtzeitig erreichbar")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.proc.kill()

    def test_health_works_with_web_port_fallback(self):
        status, body = _http_json("GET", f"{self.base_url}/health")
        self.assertEqual(status, 200)
        self.assertTrue(body.get("ok"))
