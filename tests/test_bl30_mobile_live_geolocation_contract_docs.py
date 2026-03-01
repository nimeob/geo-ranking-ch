import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30MobileLiveGeolocationContractDocs(unittest.TestCase):
    def test_mobile_geolocation_contract_doc_contains_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "api" / "mobile-live-geolocation-contract-v1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/api/mobile-live-geolocation-contract-v1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-30.6.wp1 — Mobile Live-Geolocation API-Contract v1 (additiv zu /analyze)",
            "## 2) Request-Contract (additiv)",
            "## 3) Response-Contract (additiv)",
            "## 4) Fehler- und Fallback-Semantik (deterministisch)",
            "## 6) Additive Kompatibilität zu Contract v1",
            "## 8) Definition-of-Done-Check (#502)",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in BL-30.6.wp1 Doku: {marker}")

        required_terms = [
            "options.mobile_geolocation",
            "coordinates.lat",
            "coordinates.lon",
            "result.status.mobile_geolocation",
            "permission_state",
            "battery_saver",
            "api.request.start",
            "api.request.end",
            "#503",
            "#504",
        ]
        for term in required_terms:
            self.assertIn(term, content, msg=f"Pflichtbegriff fehlt in BL-30.6.wp1 Doku: {term}")

    def test_contract_v1_references_mobile_geolocation_contract(self):
        contract_doc = (REPO_ROOT / "docs" / "api" / "contract-v1.md").read_text(encoding="utf-8")
        self.assertIn("BL-30.6-Referenz (Mobile Live-Geolocation, v1-Rahmen):", contract_doc)
        self.assertIn(
            "[`docs/api/mobile-live-geolocation-contract-v1.md`](./mobile-live-geolocation-contract-v1.md)",
            contract_doc,
        )
        self.assertIn("options.mobile_geolocation", contract_doc)
        self.assertIn("result.status.mobile_geolocation", contract_doc)

    def test_backlog_tracks_bl30_6_wp1_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn(
            "#502 — BL-30.6.wp1 Mobile Live-Geolocation API-Contract v1 (abgeschlossen 2026-03-01)",
            backlog,
        )
        self.assertIn(
            "[`docs/api/mobile-live-geolocation-contract-v1.md`](api/mobile-live-geolocation-contract-v1.md)",
            backlog,
        )
        self.assertIn("tests/test_bl30_mobile_live_geolocation_contract_docs.py", backlog)


if __name__ == "__main__":
    unittest.main()
