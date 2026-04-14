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


def _resolve_api_base_url(*, base_url: str, health_payload: dict) -> str:
    env_api_base = os.getenv("DEV_API_BASE_URL", "").strip().rstrip("/")
    if env_api_base:
        return env_api_base

    api_base_url = health_payload.get("api_base_url")
    if isinstance(api_base_url, str):
        normalized = api_base_url.strip().rstrip("/")
        if normalized.startswith(("http://", "https://")):
            return normalized

    return base_url


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

        api_base_url = _resolve_api_base_url(base_url=self.base_url, health_payload=health)

        status, version = _http_json("GET", f"{self.base_url}/version")
        if status == 404 and api_base_url != self.base_url:
            status, version = _http_json("GET", f"{api_base_url}/version")

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

        status, health = _http_json("GET", f"{self.base_url}/health")
        self.assertEqual(status, 200)
        api_base_url = _resolve_api_base_url(base_url=self.base_url, health_payload=health)

        analyze_base = self.base_url
        status, body = _http_json("POST", f"{analyze_base}/analyze", payload=payload, timeout=40)
        if status == 404 and api_base_url != self.base_url:
            analyze_base = api_base_url
            status, body = _http_json("POST", f"{analyze_base}/analyze", payload=payload, timeout=40)

        if self.dev_token:
            if status == 401:
                self.assertEqual(body.get("error"), "unauthorized")

                status, body = _http_json(
                    "POST",
                    f"{analyze_base}/analyze",
                    payload=payload,
                    headers={"Authorization": "Bearer wrong-token"},
                    timeout=40,
                )
                self.assertEqual(status, 401)
                self.assertEqual(body.get("error"), "unauthorized")

                status, body = _http_json(
                    "POST",
                    f"{analyze_base}/analyze",
                    payload=payload,
                    headers={"Authorization": f"Bearer {self.dev_token}"},
                    timeout=40,
                )
                self.assertEqual(status, 200)
                self.assertTrue(body.get("ok"))
                self.assertIn("result", body)
                return

            self.assertEqual(status, 200)
            self.assertTrue(body.get("ok"))
            return

        if status == 200:
            self.assertTrue(body.get("ok"))
            return

        self.assertEqual(status, 401)
        self.assertEqual(body.get("error"), "unauthorized")
