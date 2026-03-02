import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


REPO_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_DIR / "src"
SCRIPT = SRC_DIR / "geo_utils.py"

spec = importlib.util.spec_from_file_location("geo_utils", str(SCRIPT))
geo_utils = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = geo_utils
spec.loader.exec_module(geo_utils)


class DummyResp:
    def __init__(self, payload: dict | list):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


class TestGeoUtilsMockedHttp(unittest.TestCase):
    def test_wgs84_to_lv95_parses_float_strings(self):
        def fake_urlopen(req, timeout=0):
            self.assertIn("/wgs84tolv95?", req.full_url)
            return DummyResp({"easting": "2600000.123", "northing": "1200000.456"})

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            e, n = geo_utils.wgs84_to_lv95(47.0, 8.0)

        self.assertAlmostEqual(e, 2600000.123)
        self.assertAlmostEqual(n, 1200000.456)

    def test_lv95_to_wgs84_parses_float_strings(self):
        def fake_urlopen(req, timeout=0):
            self.assertIn("/lv95towgs84?", req.full_url)
            return DummyResp({"easting": "8.5417234", "northing": "47.3769123"})

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            lat, lon = geo_utils.lv95_to_wgs84(2600000.0, 1200000.0)

        self.assertAlmostEqual(lat, 47.3769123)
        self.assertAlmostEqual(lon, 8.5417234)

    def test_elevation_at_returns_none_on_http_error(self):
        call_count = {"n": 0}

        def fake_urlopen(req, timeout=0):
            call_count["n"] += 1
            url = req.full_url
            if "/wgs84tolv95?" in url:
                return DummyResp({"easting": "2600000", "northing": "1200000"})
            if "/height?" in url:
                raise geo_utils.urllib.error.URLError("offline")
            raise AssertionError(f"unexpected url: {url}")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            h = geo_utils.elevation_at(47.0, 8.0)

        self.assertIsNone(h)
        self.assertGreaterEqual(call_count["n"], 2)

    def test_elevation_at_returns_none_when_coordinate_conversion_fails(self):
        def fake_urlopen(req, timeout=0):
            if "/wgs84tolv95?" in req.full_url:
                raise geo_utils.urllib.error.URLError("reframe down")
            raise AssertionError("height endpoint must not be called if conversion fails")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            h = geo_utils.elevation_at(47.0, 8.0)

        self.assertIsNone(h)

    def test_geocode_ch_sanitizes_label_html_and_is_deterministic(self):
        call_count = {"n": 0}

        def fake_urlopen(req, timeout=0):
            call_count["n"] += 1
            url = req.full_url

            if "SearchServer" in url:
                # LV95 vom SearchServer: x=northing, y=easting
                return DummyResp(
                    {
                        "results": [
                            {
                                "attrs": {
                                    "label": "Wassergasse 24 <b>9000 St. Gallen</b>",
                                    "detail": "wassergasse 24 9000 st. gallen",
                                    "origin": "address",
                                    "x": 1200000.0,
                                    "y": 2600000.0,
                                    "postalcode": "9000",
                                    "city": "St. Gallen",
                                    "featureId": "123_0",
                                }
                            }
                        ]
                    }
                )

            if "/lv95towgs84?" in url:
                return DummyResp({"easting": "8.5417234", "northing": "47.3769123"})

            raise AssertionError(f"unexpected url: {url}")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            res = geo_utils.geocode_ch("Wassergasse 24 9000 St. Gallen", origins="address", limit=1)

        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["label"], "Wassergasse 24 9000 St. Gallen")
        self.assertAlmostEqual(res[0]["lat"], 47.3769123, places=7)
        self.assertAlmostEqual(res[0]["lon"], 8.5417234, places=7)
        self.assertEqual(res[0]["zip_code"], "9000")
        self.assertEqual(res[0]["city"], "St. Gallen")

        # SearchServer + lv95towgs84 (conversion)
        self.assertEqual(call_count["n"], 2)


if __name__ == "__main__":
    unittest.main()
