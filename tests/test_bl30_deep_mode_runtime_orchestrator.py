import os
import unittest
from unittest.mock import patch

from src.api.web_service import _apply_deep_mode_runtime_status, _grouped_api_result


_RUNTIME_ENV_DEFAULTS = {
    "DEEP_BASELINE_RESERVED_FLOOR_MS": "1000",
    "DEEP_BASELINE_RESERVED_RATIO": "0.7",
    "DEEP_SAFETY_MARGIN_MS": "250",
    "DEEP_MIN_BUDGET_MS": "600",
    "DEEP_MAX_TOKENS_SERVER": "12000",
    "DEEP_PROFILE_CAP_ANALYSIS_PLUS": "12000",
    "DEEP_PROFILE_CAP_RISK_PLUS": "9000",
}


class TestBL30DeepModeRuntimeOrchestrator(unittest.TestCase):
    def _status_for(
        self,
        *,
        options: dict,
        timeout_seconds: float = 5.0,
        intelligence_mode: str = "basic",
    ) -> tuple[dict, dict]:
        report: dict = {}
        with patch.dict(os.environ, _RUNTIME_ENV_DEFAULTS, clear=False):
            _apply_deep_mode_runtime_status(
                report,
                options=options,
                intelligence_mode=intelligence_mode,
                timeout_seconds=timeout_seconds,
            )

        grouped = _grouped_api_result(report, response_mode="compact")
        status = grouped.get("status", {})
        capabilities = status.get("capabilities", {}).get("deep_mode", {})
        entitlements = status.get("entitlements", {}).get("deep_mode", {})
        return capabilities, entitlements

    def test_fallback_matrix_covers_gate_paths(self):
        matrix_cases = [
            {
                "name": "deep_not_requested",
                "options": {},
                "timeout_seconds": 5.0,
                "expected": {
                    "requested": False,
                    "effective": False,
                    "fallback_reason": None,
                    "allowed": False,
                    "quota_consumed": 0,
                    "quota_remaining": None,
                },
            },
            {
                "name": "not_entitled",
                "options": {
                    "capabilities": {"deep_mode": {"requested": True, "profile": "analysis_plus"}},
                    "entitlements": {"deep_mode": {"allowed": False, "quota_remaining": 4}},
                },
                "timeout_seconds": 5.0,
                "expected": {
                    "requested": True,
                    "effective": False,
                    "fallback_reason": "not_entitled",
                    "allowed": False,
                    "quota_consumed": 0,
                    "quota_remaining": 4,
                },
            },
            {
                "name": "quota_exhausted",
                "options": {
                    "capabilities": {"deep_mode": {"requested": True, "profile": "analysis_plus"}},
                    "entitlements": {"deep_mode": {"allowed": True, "quota_remaining": 0}},
                },
                "timeout_seconds": 5.0,
                "expected": {
                    "requested": True,
                    "effective": False,
                    "fallback_reason": "quota_exhausted",
                    "allowed": True,
                    "quota_consumed": 0,
                    "quota_remaining": 0,
                },
            },
            {
                "name": "timeout_budget",
                "options": {
                    "capabilities": {"deep_mode": {"requested": True, "profile": "analysis_plus"}},
                    "entitlements": {"deep_mode": {"allowed": True, "quota_remaining": 5}},
                },
                "timeout_seconds": 0.5,
                "expected": {
                    "requested": True,
                    "effective": False,
                    "fallback_reason": "timeout_budget",
                    "allowed": True,
                    "quota_consumed": 0,
                    "quota_remaining": 5,
                },
            },
            {
                "name": "policy_guard",
                "options": {
                    "capabilities": {"deep_mode": {"requested": True, "profile": "unknown_profile"}},
                    "entitlements": {"deep_mode": {"allowed": True, "quota_remaining": 7}},
                },
                "timeout_seconds": 5.0,
                "expected": {
                    "requested": True,
                    "effective": False,
                    "fallback_reason": "policy_guard",
                    "allowed": True,
                    "quota_consumed": 0,
                    "quota_remaining": 7,
                },
            },
            {
                "name": "eligible_deep_run",
                "options": {
                    "capabilities": {
                        "deep_mode": {
                            "requested": True,
                            "profile": "analysis_plus",
                            "max_budget_tokens": 8000,
                        }
                    },
                    "entitlements": {"deep_mode": {"allowed": True, "quota_remaining": 3}},
                },
                "timeout_seconds": 5.0,
                "expected": {
                    "requested": True,
                    "effective": True,
                    "fallback_reason": None,
                    "allowed": True,
                    "quota_consumed": 1,
                    "quota_remaining": 2,
                },
            },
        ]

        for case in matrix_cases:
            with self.subTest(case=case["name"]):
                capabilities, entitlements = self._status_for(
                    options=case["options"],
                    timeout_seconds=case["timeout_seconds"],
                )
                expected = case["expected"]

                self.assertEqual(capabilities.get("requested"), expected["requested"])
                self.assertEqual(capabilities.get("effective"), expected["effective"])

                if expected["fallback_reason"] is None:
                    self.assertNotIn("fallback_reason", capabilities)
                else:
                    self.assertEqual(capabilities.get("fallback_reason"), expected["fallback_reason"])

                self.assertEqual(entitlements.get("allowed"), expected["allowed"])
                self.assertEqual(entitlements.get("quota_consumed"), expected["quota_consumed"])

                if expected["quota_remaining"] is None:
                    self.assertNotIn("quota_remaining", entitlements)
                else:
                    self.assertEqual(entitlements.get("quota_remaining"), expected["quota_remaining"])

    def test_rejects_invalid_deep_mode_types(self):
        report: dict = {}
        invalid_options = {
            "capabilities": {"deep_mode": {"requested": "yes"}},
            "entitlements": {"deep_mode": {"allowed": True, "quota_remaining": 1}},
        }

        with patch.dict(os.environ, _RUNTIME_ENV_DEFAULTS, clear=False):
            with self.assertRaises(ValueError):
                _apply_deep_mode_runtime_status(
                    report,
                    options=invalid_options,
                    intelligence_mode="basic",
                    timeout_seconds=5.0,
                )


if __name__ == "__main__":
    unittest.main()
