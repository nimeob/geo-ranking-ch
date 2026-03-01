import os
import unittest
from unittest.mock import patch

from src.api.web_service import _apply_deep_mode_runtime_status


_RUNTIME_ENV_DEFAULTS = {
    "DEEP_BASELINE_RESERVED_FLOOR_MS": "1000",
    "DEEP_BASELINE_RESERVED_RATIO": "0.7",
    "DEEP_SAFETY_MARGIN_MS": "250",
    "DEEP_MIN_BUDGET_MS": "600",
    "DEEP_MAX_TOKENS_SERVER": "12000",
    "DEEP_PROFILE_CAP_ANALYSIS_PLUS": "12000",
    "DEEP_PROFILE_CAP_RISK_PLUS": "9000",
}


class TestBL30DeepModeTelemetryEvents(unittest.TestCase):
    def setUp(self) -> None:
        self.events: list[dict] = []

        def _capture(*args, **kwargs):
            if kwargs:
                self.events.append(dict(kwargs))

        self._patcher = patch("src.api.web_service._emit_structured_log", side_effect=_capture)
        self._patcher.start()

    def tearDown(self) -> None:
        self._patcher.stop()

    def _run_apply(
        self,
        *,
        options: dict,
        timeout_seconds: float = 5.0,
        execution_retry_count: int = 0,
    ) -> None:
        report: dict = {}
        with patch.dict(os.environ, _RUNTIME_ENV_DEFAULTS, clear=False):
            _apply_deep_mode_runtime_status(
                report,
                options=options,
                intelligence_mode="basic",
                timeout_seconds=timeout_seconds,
                request_id="req-deep-telemetry",
                session_id="sess-deep-telemetry",
                execution_retry_count=execution_retry_count,
            )

    def _event(self, name: str) -> dict:
        for event in self.events:
            if event.get("event") == name:
                return event
        self.fail(f"Event fehlt: {name}")

    def _assert_required_deep_fields(self, event: dict) -> None:
        self.assertEqual(event.get("request_id"), "req-deep-telemetry")
        self.assertEqual(event.get("session_id"), "sess-deep-telemetry")
        self.assertIn("deep_requested", event)
        self.assertIn("deep_effective", event)
        self.assertIn("deep_profile", event)
        self.assertIsInstance(event.get("deep_budget_ms"), int)
        self.assertGreaterEqual(int(event.get("deep_budget_ms", -1)), 0)
        self.assertIsInstance(event.get("deep_budget_tokens_effective"), int)
        self.assertGreaterEqual(int(event.get("deep_budget_tokens_effective", -1)), 0)

    def test_eligible_flow_emits_gate_start_end_with_required_fields(self):
        self._run_apply(
            options={
                "capabilities": {
                    "deep_mode": {
                        "requested": True,
                        "profile": "analysis_plus",
                        "max_budget_tokens": 8000,
                    }
                },
                "entitlements": {"deep_mode": {"allowed": True, "quota_remaining": 2}},
            }
        )

        gate_event = self._event("api.deep_mode.gate_evaluated")
        start_event = self._event("api.deep_mode.execution.start")
        end_event = self._event("api.deep_mode.execution.end")

        for event in (gate_event, start_event, end_event):
            self._assert_required_deep_fields(event)

        self.assertEqual(gate_event.get("status"), "evaluated")
        self.assertEqual(start_event.get("status"), "started")
        self.assertEqual(end_event.get("status"), "ok")
        self.assertEqual(end_event.get("deep_effective"), True)
        self.assertIn("duration_ms", end_event)
        self.assertGreaterEqual(float(end_event.get("duration_ms", -1.0)), 0.0)

    def test_blocked_flow_emits_gate_and_abort_with_fallback_reason(self):
        self._run_apply(
            options={
                "capabilities": {"deep_mode": {"requested": True, "profile": "analysis_plus"}},
                "entitlements": {"deep_mode": {"allowed": False, "quota_remaining": 4}},
            }
        )

        gate_event = self._event("api.deep_mode.gate_evaluated")
        abort_event = self._event("api.deep_mode.execution.abort")

        self._assert_required_deep_fields(gate_event)
        self._assert_required_deep_fields(abort_event)

        self.assertEqual(abort_event.get("status"), "aborted")
        self.assertEqual(abort_event.get("fallback_reason"), "not_entitled")
        self.assertEqual(abort_event.get("deep_effective"), False)
        self.assertIn("duration_ms", abort_event)
        self.assertGreaterEqual(float(abort_event.get("duration_ms", -1.0)), 0.0)

        event_names = [str(event.get("event")) for event in self.events]
        self.assertNotIn("api.deep_mode.execution.end", event_names)

    def test_retry_event_includes_retry_count_when_provided(self):
        self._run_apply(
            options={
                "capabilities": {"deep_mode": {"requested": True, "profile": "analysis_plus"}},
                "entitlements": {"deep_mode": {"allowed": True, "quota_remaining": 2}},
            },
            execution_retry_count=2,
        )

        retry_event = self._event("api.deep_mode.execution.retry")
        self._assert_required_deep_fields(retry_event)
        self.assertEqual(retry_event.get("status"), "retrying")
        self.assertEqual(retry_event.get("retry_count"), 2)


if __name__ == "__main__":
    unittest.main()
