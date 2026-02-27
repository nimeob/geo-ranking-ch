import unittest
from unittest import mock

from src import web_service
from src.web_service import (
    _attach_coordinate_resolution_context,
    _extract_query_and_coordinate_context,
)


class TestWebServiceCoordinateInput(unittest.TestCase):
    def test_prefers_explicit_query_when_present(self):
        query, context = _extract_query_and_coordinate_context(
            {
                "query": " Bahnhofstrasse 1, 8001 Zürich ",
                "coordinates": {"lat": 47.3769, "lon": 8.5417},
            }
        )

        self.assertEqual(query, "Bahnhofstrasse 1, 8001 Zürich")
        self.assertIsNone(context)

    def test_resolves_coordinates_with_default_snap_mode(self):
        resolved_query = "Spisergasse 6, 9000 St. Gallen"
        resolved_meta = {
            "provider": "ch.bfs.gebaeude_wohnungs_register",
            "feature_id": "1072597_0",
            "distance_m": 12.4,
            "resolved_query": resolved_query,
            "clickpoint_wgs84": {"lat": 47.4245, "lon": 9.3767},
        }

        with mock.patch.object(
            web_service,
            "_resolve_query_from_coordinates",
            return_value=(resolved_query, resolved_meta),
        ) as resolver:
            query, context = _extract_query_and_coordinate_context(
                {
                    "coordinates": {
                        "lat": "47.4245",
                        "lon": "9.3767",
                    }
                }
            )

        self.assertEqual(query, resolved_query)
        self.assertIsInstance(context, dict)
        self.assertEqual(context.get("input_mode"), "coordinates")
        self.assertEqual(context.get("snap_mode"), "ch_bounds")
        self.assertFalse(context.get("snap_applied"))
        resolver.assert_called_once_with(lat=47.4245, lon=9.3767)

    def test_snaps_near_border_in_ch_bounds_mode(self):
        min_lat = float(web_service._CH_WGS84_BOUNDS["lat_min"])

        with mock.patch.object(
            web_service,
            "_resolve_query_from_coordinates",
            return_value=("Rue du Lac 1, 1290 Versoix", {"feature_id": "f1"}),
        ) as resolver:
            query, context = _extract_query_and_coordinate_context(
                {
                    "coordinates": {
                        "lat": min_lat - 0.005,
                        "lon": 6.05,
                    }
                }
            )

        self.assertEqual(query, "Rue du Lac 1, 1290 Versoix")
        self.assertTrue(context.get("snap_applied"))
        resolver.assert_called_once()
        kwargs = resolver.call_args.kwargs
        self.assertAlmostEqual(kwargs["lat"], min_lat, places=6)

    def test_rejects_coordinates_outside_swiss_bounds_when_tolerance_exceeded(self):
        with self.assertRaises(ValueError) as ctx:
            _extract_query_and_coordinate_context(
                {
                    "coordinates": {
                        "lat": 40.0,
                        "lon": 9.3767,
                    }
                }
            )

        self.assertIn("outside Swiss coverage bounds", str(ctx.exception))

    def test_rejects_invalid_snap_mode(self):
        with self.assertRaises(ValueError) as ctx:
            _extract_query_and_coordinate_context(
                {
                    "coordinates": {
                        "lat": 47.0,
                        "lon": 8.0,
                        "snap_mode": "nearest",
                    }
                }
            )

        self.assertIn("coordinates.snap_mode", str(ctx.exception))

    def test_attach_coordinate_resolution_context_is_additive(self):
        report = {
            "match": {
                "resolution": {
                    "pipeline_version": "v1",
                }
            }
        }

        _attach_coordinate_resolution_context(
            report,
            {
                "input_mode": "coordinates",
                "snap_mode": "ch_bounds",
                "snap_applied": False,
                "resolved": {"feature_id": "f2"},
            },
        )

        resolution = report["match"]["resolution"]
        self.assertEqual(resolution.get("pipeline_version"), "v1")
        self.assertEqual(resolution.get("input_mode"), "coordinates")
        self.assertIn("coordinate_input", resolution)


if __name__ == "__main__":
    unittest.main()
