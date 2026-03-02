import json
import os
import unittest
from unittest.mock import patch

from src.api import web_service


_RUNTIME_ENV_DEFAULTS = {
    "DEEP_BASELINE_RESERVED_FLOOR_MS": "1000",
    "DEEP_BASELINE_RESERVED_RATIO": "0.7",
    "DEEP_SAFETY_MARGIN_MS": "250",
    "DEEP_MIN_BUDGET_MS": "600",
    "DEEP_MAX_TOKENS_SERVER": "12000",
    "DEEP_PROFILE_CAP_ANALYSIS_PLUS": "12000",
    "DEEP_PROFILE_CAP_RISK_PLUS": "9000",
    "DEEP_OPEN_METEO_MAX_ATTEMPTS": "1",
    "DEEP_OPEN_METEO_BACKOFF_SECONDS": "0",
    "DEEP_OPEN_METEO_MIN_INTERVAL_SECONDS": "0",
    "DEEP_OPEN_METEO_CACHE_TTL_SECONDS": "0",
}


class _FakeResponse:
    def __init__(self, payload: dict, *, status: int = 200):
        self.status = status
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestWP704OpenMeteoDeepEnrichment(unittest.TestCase):
    def setUp(self) -> None:
        web_service._OPEN_METEO_CACHE.clear()
        web_service._OPEN_METEO_LAST_REQUEST_TS = 0.0

    def test_deep_enrichment_attached_when_deep_mode_effective(self):
        report: dict = {
            "coordinates": {"lat": 47.3769, "lon": 8.5417},
            "sources": {},
            "source_classification": {},
            "source_attribution": {},
        }
        options = {
            "capabilities": {"deep_mode": {"requested": True, "profile": "analysis_plus"}},
            "entitlements": {"deep_mode": {"allowed": True, "quota_remaining": 2}},
        }

        upstream_payload = {
            "latitude": 47.3769,
            "longitude": 8.5417,
            "timezone": "UTC",
            "utc_offset_seconds": 0,
            "current": {
                "time": "2026-03-02T03:00",
                "temperature_2m": 6.2,
                "relative_humidity_2m": 71,
                "precipitation": 0.0,
                "wind_speed_10m": 3.4,
            },
        }

        with patch.dict(os.environ, _RUNTIME_ENV_DEFAULTS, clear=False):
            with patch("src.api.web_service.urlopen", return_value=_FakeResponse(upstream_payload)) as mocked:
                web_service._apply_open_meteo_deep_enrichment(
                    report,
                    options=options,
                    intelligence_mode="basic",
                    timeout_seconds=5.0,
                )

        self.assertIn("deep_enrichment", report)
        module = report["deep_enrichment"]
        self.assertEqual(module.get("provider"), "open-meteo")
        self.assertEqual(module.get("source"), "open_meteo_forecast")
        self.assertGreaterEqual(float(module.get("confidence") or 0.0), 0.7)
        self.assertEqual(module.get("fetch", {}).get("ok"), True)
        self.assertIn("forecast", module)
        self.assertIn("current", module.get("forecast") or {})

        self.assertIn("open_meteo_forecast", report.get("sources") or {})
        self.assertEqual(report["sources"]["open_meteo_forecast"].get("status"), "ok")

        self.assertIn("open_meteo_forecast", report.get("source_classification") or {})
        self.assertIn("deep_enrichment", report.get("source_attribution") or {})
        self.assertIn("open_meteo_forecast", report["source_attribution"]["deep_enrichment"])

        called_url = str(mocked.call_args[0][0])
        self.assertIn("api.open-meteo.com", called_url)


if __name__ == "__main__":
    unittest.main()
