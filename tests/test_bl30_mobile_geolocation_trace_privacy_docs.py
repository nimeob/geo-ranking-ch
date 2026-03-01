import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30MobileGeolocationTracePrivacyDocs(unittest.TestCase):
    def test_mobile_trace_privacy_doc_contains_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "testing" / "MOBILE_GEOLOCATION_TRACE_PRIVACY_V1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/testing/MOBILE_GEOLOCATION_TRACE_PRIVACY_V1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-30.6.wp3 — Mobile Geolocation Trace-/Privacy-Guardrails v1",
            "## 2) Mindestevent-Liste (Mobile-Geolocation-Lifecycle)",
            "## 3) Privacy-/Redaction-Regeln pro Feldklasse",
            "## 4) Trace-Evidence-Nachweisformat (verbindlich)",
            "## 6) Definition-of-Done-Check (#504)",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in BL-30.6.wp3 Doku: {marker}")

        required_terms = [
            "ui.mobile.permission.state",
            "ui.mobile.locate.start",
            "ui.mobile.locate.end",
            "ui.mobile.offline.state",
            "ui.mobile.retry.triggered",
            "privacy_class",
            "redaction_applied",
            "coordinates.lat",
            "coordinates.lon",
            "authorization",
            "api_key",
            "trace_id",
            "request_id",
            "session_id",
        ]
        for term in required_terms:
            self.assertIn(term, content, msg=f"Pflichtbegriff fehlt in BL-30.6.wp3 Doku: {term}")

    def test_logging_schema_and_mobile_contract_reference_wp3_guardrails(self):
        logging_schema = (REPO_ROOT / "docs" / "LOGGING_SCHEMA_V1.md").read_text(encoding="utf-8")
        self.assertIn("## BL-30.6.wp3 Mobile-Geolocation Trace-/Privacy-Guardrails", logging_schema)
        self.assertIn("docs/testing/MOBILE_GEOLOCATION_TRACE_PRIVACY_V1.md", logging_schema)
        self.assertIn("tests/test_bl30_mobile_geolocation_trace_privacy_docs.py", logging_schema)

        mobile_contract = (
            REPO_ROOT / "docs" / "api" / "mobile-live-geolocation-contract-v1.md"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "docs/testing/MOBILE_GEOLOCATION_TRACE_PRIVACY_V1.md",
            mobile_contract,
        )

    def test_backlog_tracks_bl30_6_wp3_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn(
            "#504 — BL-30.6.wp3 Mobile Geolocation Trace-/Privacy-Guardrails v1 (abgeschlossen 2026-03-01)",
            backlog,
        )
        self.assertIn(
            "[`docs/testing/MOBILE_GEOLOCATION_TRACE_PRIVACY_V1.md`](testing/MOBILE_GEOLOCATION_TRACE_PRIVACY_V1.md)",
            backlog,
        )
        self.assertIn("tests/test_bl30_mobile_geolocation_trace_privacy_docs.py", backlog)


if __name__ == "__main__":
    unittest.main()
