import unittest
from unittest.mock import patch

from src.api import address_intel


def _pois(n: int) -> list[dict]:
    return [{"name": f"poi-{i}", "category": "amenity", "subcategory": "cafe"} for i in range(n)]


class TestFetchOsmPoiOverpassAdaptive(unittest.TestCase):
    def test_normal_no_fallback_when_threshold_met(self):
        calls: list[int] = []

        def _fake_fetch(_client, _sources, *, lat, lon, radius_m, max_items):
            calls.append(int(radius_m))
            return {"source_url": "https://overpass.example", "pois": _pois(30)}

        with patch("src.api.address_intel.fetch_osm_poi_overpass", side_effect=_fake_fetch):
            payload, meta = address_intel.fetch_osm_poi_overpass_adaptive(
                client=object(),
                sources=address_intel.SourceRegistry(),
                lat=47.0,
                lon=8.0,
                radius_m=200,
                max_items=200,
                thin_poi_threshold=18,
                max_steps=2,
                radius_growth=1.6,
                max_radius_m=900,
            )

        self.assertEqual(len(payload.get("pois") or []), 30)
        self.assertEqual(calls, [200])
        self.assertEqual(meta.get("fallback_applied"), False)
        self.assertEqual(meta.get("low_confidence"), False)
        self.assertEqual(meta.get("limit_reached"), False)
        self.assertEqual(len(meta.get("attempts") or []), 1)

    def test_fallback_applied_then_threshold_met(self):
        calls: list[int] = []
        responses = [
            {"source_url": "https://overpass.example", "pois": _pois(10)},
            {"source_url": "https://overpass.example", "pois": _pois(22)},
        ]

        def _fake_fetch(_client, _sources, *, lat, lon, radius_m, max_items):
            calls.append(int(radius_m))
            return responses[len(calls) - 1]

        with patch("src.api.address_intel.fetch_osm_poi_overpass", side_effect=_fake_fetch):
            payload, meta = address_intel.fetch_osm_poi_overpass_adaptive(
                client=object(),
                sources=address_intel.SourceRegistry(),
                lat=47.0,
                lon=8.0,
                radius_m=200,
                max_items=200,
                thin_poi_threshold=18,
                max_steps=2,
                radius_growth=1.6,
                max_radius_m=900,
            )

        self.assertEqual(calls, [200, 320])
        self.assertEqual(len(payload.get("pois") or []), 22)
        self.assertEqual(meta.get("fallback_applied"), True)
        self.assertEqual(meta.get("limit_reached"), False)
        self.assertEqual(meta.get("low_confidence"), True)
        self.assertIn("fallback_applied", meta.get("reason") or "")
        self.assertEqual(len(meta.get("attempts") or []), 2)

    def test_fallback_limit_reached(self):
        calls: list[int] = []
        responses = [
            {"source_url": "https://overpass.example", "pois": _pois(5)},
            {"source_url": "https://overpass.example", "pois": _pois(7)},
            {"source_url": "https://overpass.example", "pois": _pois(9)},
        ]

        def _fake_fetch(_client, _sources, *, lat, lon, radius_m, max_items):
            calls.append(int(radius_m))
            return responses[len(calls) - 1]

        with patch("src.api.address_intel.fetch_osm_poi_overpass", side_effect=_fake_fetch):
            payload, meta = address_intel.fetch_osm_poi_overpass_adaptive(
                client=object(),
                sources=address_intel.SourceRegistry(),
                lat=47.0,
                lon=8.0,
                radius_m=200,
                max_items=200,
                thin_poi_threshold=18,
                max_steps=2,
                radius_growth=1.6,
                max_radius_m=900,
            )

        self.assertEqual(calls, [200, 320, 512])
        self.assertEqual(len(payload.get("pois") or []), 9)
        self.assertEqual(meta.get("fallback_applied"), True)
        self.assertEqual(meta.get("limit_reached"), True)
        self.assertEqual(meta.get("low_confidence"), True)
        self.assertIn("fallback_limit_reached", meta.get("reason") or "")
        self.assertEqual(len(meta.get("attempts") or []), 3)


class TestBuildIntelligenceLayersLowConfidenceSignal(unittest.TestCase):
    def test_build_intelligence_layers_sets_low_confidence_on_environment_profile(self):
        client = address_intel.HttpClient(
            timeout=1,
            retries=0,
            backoff_seconds=0.01,
            min_request_interval_seconds=0.0,
            cache_ttl_seconds=0.0,
            enable_disk_cache=False,
        )
        sources = address_intel.SourceRegistry()
        query = address_intel.QueryParts(
            raw="Some Street 1, 9000 St. Gallen",
            normalized="some street 1 9000 st. gallen",
            street="Some Street",
            house_number="1",
            postal_code="9000",
            city="St. Gallen",
            tokens=["some", "street", "1", "9000", "st.", "gallen"],
        )
        selected = address_intel.CandidateEval(
            feature_id="feat-1",
            label="Some Street 1",
            detail="detail",
            origin=None,
            rank=1,
            lat=47.0,
            lon=8.0,
            pre_score=1.0,
        )

        poi_payload = {"source_url": "https://overpass.example", "pois": _pois(3)}
        poi_meta = {
            "low_confidence": True,
            "limit_reached": True,
            "reason": "fallback_limit_reached: poi_count=3 < threshold=18 (final_radius=512m)",
            "attempts": [{"radius_m": 200, "poi_count": 1}, {"radius_m": 320, "poi_count": 2}, {"radius_m": 512, "poi_count": 3}],
        }

        with patch(
            "src.api.address_intel.fetch_osm_poi_overpass_adaptive",
            return_value=(poi_payload, poi_meta),
        ), patch(
            "src.api.address_intel.build_tenants_businesses_layer",
            return_value={"status": "ok", "entities": [], "statements": []},
        ), patch(
            "src.api.address_intel.build_environment_noise_risk_layer",
            return_value={"status": "ok", "statements": []},
        ), patch(
            "src.api.address_intel.build_environment_profile_layer",
            return_value={"status": "ok", "statements": []},
        ), patch(
            "src.api.address_intel.fetch_google_news_rss",
            return_value={"events": []},
        ), patch(
            "src.api.address_intel.build_incidents_timeline_layer",
            return_value={"status": "ok", "events": [], "statements": []},
        ), patch(
            "src.api.address_intel.build_consistency_checks_layer",
            return_value={"status": "ok"},
        ), patch(
            "src.api.address_intel.build_executive_risk_summary",
            return_value={"status": "ok"},
        ):
            result = address_intel.build_intelligence_layers(
                mode="extended",
                client=client,
                sources=sources,
                query=query,
                selected=selected,
                confidence={"ambiguity": {}},
                plz_layer={},
                admin_boundary={},
            )

        env = result.get("environment_profile") or {}
        self.assertEqual(env.get("low_confidence"), True)
        self.assertIn("fallback", env)
        self.assertIn("low_confidence_reason", env)
        statements = env.get("statements") or []
        self.assertGreaterEqual(len(statements), 1)
        self.assertIn("Fallback-Limit erreicht", statements[0].get("text") or "")


if __name__ == "__main__":
    unittest.main()
