import json
import os
import unittest
from unittest import mock

from src import web_service


class DummyResponse:
    def __init__(self, payload: dict, *, status: int = 200):
        self._payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


class TestWebServiceDevGeoCache(unittest.TestCase):
    def setUp(self):
        web_service._DEV_GEO_QUERY_CACHE.clear()

    def test_fetch_json_url_cache_hit_when_enabled(self):
        call_count = {"n": 0}

        def fake_urlopen(url, timeout=0):
            call_count["n"] += 1
            self.assertIn("example.test", str(url))
            return DummyResponse({"results": [{"id": 1}]})

        with mock.patch.dict(
            os.environ,
            {
                "DEV_GEO_QUERY_CACHE_TTL_SECONDS": "60",
                "DEV_GEO_QUERY_CACHE_DISK": "0",
            },
            clear=False,
        ):
            with mock.patch.object(web_service, "urlopen", side_effect=fake_urlopen):
                first = web_service._fetch_json_url(
                    "https://example.test/api?x=1",
                    timeout_seconds=1.0,
                    source="unit",
                    upstream_log_emitter=None,
                )
                second = web_service._fetch_json_url(
                    "https://example.test/api?x=1",
                    timeout_seconds=1.0,
                    source="unit",
                    upstream_log_emitter=None,
                )

        self.assertEqual(first, {"results": [{"id": 1}]})
        self.assertEqual(second, {"results": [{"id": 1}]})
        self.assertEqual(call_count["n"], 1)

    def test_fetch_json_url_cache_miss_when_disabled(self):
        call_count = {"n": 0}

        def fake_urlopen(url, timeout=0):
            call_count["n"] += 1
            return DummyResponse({"results": []})

        with mock.patch.dict(
            os.environ,
            {
                "DEV_GEO_QUERY_CACHE_TTL_SECONDS": "0",
                "DEV_GEO_QUERY_CACHE_DISK": "0",
            },
            clear=False,
        ):
            with mock.patch.object(web_service, "urlopen", side_effect=fake_urlopen):
                web_service._fetch_json_url(
                    "https://example.test/api?x=2",
                    timeout_seconds=1.0,
                    source="unit",
                    upstream_log_emitter=None,
                )
                web_service._fetch_json_url(
                    "https://example.test/api?x=2",
                    timeout_seconds=1.0,
                    source="unit",
                    upstream_log_emitter=None,
                )

        self.assertEqual(call_count["n"], 2)


if __name__ == "__main__":
    unittest.main()
