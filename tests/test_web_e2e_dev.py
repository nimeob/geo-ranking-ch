import json
import os
import unittest
from urllib import error, request


def _http_json(method: str, url: str, payload=None, headers=None, timeout: float = 20.0):
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
            return resp.status, json.loads(body)
    except error.HTTPError as e:
        body = e.read().decode("utf-8")
        parsed = json.loads(body) if body else {}
        return e.code, parsed


@unittest.skipUnless(os.getenv("DEV_BASE_URL"), "DEV_BASE_URL nicht gesetzt")
class TestWebServiceE2EDev(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_url = os.environ["DEV_BASE_URL"].rstrip("/")
        cls.dev_token = os.getenv("DEV_API_AUTH_TOKEN", "").strip()

    def test_dev_health_version_not_found(self):
        status, health = _http_json("GET", f"{self.base_url}/health")
        self.assertEqual(status, 200)
        self.assertTrue(health.get("ok"))

        status, version = _http_json("GET", f"{self.base_url}/version")
        self.assertEqual(status, 200)
        self.assertIn("service", version)

        status, body = _http_json("GET", f"{self.base_url}/definitely-missing")
        self.assertEqual(status, 404)
        self.assertEqual(body.get("error"), "not_found")

    def test_dev_analyze_with_optional_auth(self):
        payload = {
            "query": "Bahnhofstrasse 1, 8001 Zürich",
            "intelligence_mode": "basic",
            "timeout_seconds": 4,
        }

        if self.dev_token:
            status, body = _http_json("POST", f"{self.base_url}/analyze", payload=payload)
            self.assertEqual(status, 401)
            self.assertEqual(body.get("error"), "unauthorized")

            status, body = _http_json(
                "POST",
                f"{self.base_url}/analyze",
                payload=payload,
                headers={"Authorization": "Bearer wrong-token"},
                timeout=40,
            )
            self.assertEqual(status, 401)
            self.assertEqual(body.get("error"), "unauthorized")

            status, body = _http_json(
                "POST",
                f"{self.base_url}/analyze",
                payload=payload,
                headers={"Authorization": f"Bearer {self.dev_token}"},
                timeout=40,
            )
            self.assertEqual(status, 200)
            self.assertTrue(body.get("ok"))
            self.assertIn("result", body)
            return

        status, body = _http_json("POST", f"{self.base_url}/analyze", payload=payload, timeout=40)
        self.assertEqual(status, 200)
        self.assertTrue(body.get("ok"))
