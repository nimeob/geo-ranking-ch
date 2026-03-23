import unittest
from unittest import mock

from src import web_service
from src.web_service import (
    _attach_coordinate_resolution_context,
    _extract_query_and_coordinate_context,
    _resolve_query_from_coordinates,
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
        resolver.assert_called_once_with(
            lat=47.4245,
            lon=9.3767,
            upstream_log_emitter=None,
        )

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

    def test_rejects_non_finite_coordinate_values(self):
        cases = [
            (float("nan"), 8.0, "coordinates.lat must be a finite number"),
            (float("-inf"), 8.0, "coordinates.lat must be a finite number"),
            (47.0, float("inf"), "coordinates.lon must be a finite number"),
            ("", 8.0, "coordinates.lat must be a finite number"),
            ("   ", 8.0, "coordinates.lat must be a finite number"),
            ("nan", 8.0, "coordinates.lat must be a finite number"),
            (47.0, "", "coordinates.lon must be a finite number"),
            (47.0, "   ", "coordinates.lon must be a finite number"),
            (47.0, "inf", "coordinates.lon must be a finite number"),
        ]

        for raw_lat, raw_lon, expected_error in cases:
            with self.subTest(raw_lat=raw_lat, raw_lon=raw_lon):
                with self.assertRaises(ValueError) as ctx:
                    _extract_query_and_coordinate_context(
                        {
                            "coordinates": {
                                "lat": raw_lat,
                                "lon": raw_lon,
                            }
                        }
                    )

                self.assertIn(expected_error, str(ctx.exception))

    def test_rejects_coordinates_missing_required_fields(self):
        cases = [
            ({"lon": 8.0}, "coordinates.lat and coordinates.lon are required"),
            ({"lat": 47.0}, "coordinates.lat and coordinates.lon are required"),
            ({"lng": 8.0}, "coordinates.lat and coordinates.lon are required"),
        ]

        for coordinates, expected_error in cases:
            with self.subTest(coordinates=coordinates):
                with self.assertRaises(ValueError) as ctx:
                    _extract_query_and_coordinate_context({"coordinates": coordinates})

                self.assertIn(expected_error, str(ctx.exception))

    def test_rejects_coordinates_outside_lat_lon_range(self):
        cases = [
            ({"lat": 100.0, "lon": 8.0}, "coordinates.lat must be between -90 and 90"),
            ({"lat": -100.0, "lon": 8.0}, "coordinates.lat must be between -90 and 90"),
            ({"lat": 47.0, "lon": 200.0}, "coordinates.lon must be between -180 and 180"),
            ({"lat": 47.0, "lon": -200.0}, "coordinates.lon must be between -180 and 180"),
        ]

        for coordinates, expected_error in cases:
            with self.subTest(coordinates=coordinates):
                with self.assertRaises(ValueError) as ctx:
                    _extract_query_and_coordinate_context({"coordinates": coordinates})

                self.assertIn(expected_error, str(ctx.exception))

    def test_coordinate_resolution_uses_expanded_identify_fallback(self):
        with mock.patch.object(web_service, "_wgs84_to_lv95", return_value=(2600000.0, 1200000.0)), mock.patch.object(
            web_service,
            "_identify_gwr_candidates",
            side_effect=[
                [],
                [
                    {
                        "street": "Bahnhofstrasse 1",
                        "postal_code": "9000",
                        "city": "St. Gallen",
                        "lv95_e": 2600200.0,
                        "lv95_n": 1200000.0,
                        "feature_id": "f-1",
                    }
                ],
            ],
        ) as identify:
            query, resolved = _resolve_query_from_coordinates(lat=47.42, lon=9.37)

        self.assertEqual(query, "Bahnhofstrasse 1, 9000 St. Gallen")
        self.assertEqual(resolved.get("fallback", {}).get("strategy"), "expanded_gwr_identify")
        self.assertEqual(identify.call_count, 2)
        first_call = identify.call_args_list[0].kwargs
        second_call = identify.call_args_list[1].kwargs
        self.assertEqual(first_call.get("identify_tolerance_m"), web_service._COORDINATE_IDENTIFY_TOLERANCE_M)
        self.assertEqual(second_call.get("identify_tolerance_m"), web_service._COORDINATE_FALLBACK_IDENTIFY_RADII_M[0])

    def test_coordinate_resolution_returns_actionable_error_when_no_candidates(self):
        with mock.patch.object(web_service, "_wgs84_to_lv95", return_value=(2600000.0, 1200000.0)), mock.patch.object(
            web_service,
            "_identify_gwr_candidates",
            side_effect=[[], [], []],
        ):
            with self.assertRaises(ValueError) as ctx:
                _resolve_query_from_coordinates(lat=47.42, lon=9.37)

        self.assertIn("no identify match up to", str(ctx.exception))

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
