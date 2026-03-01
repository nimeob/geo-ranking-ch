"""Tests for compliance correction API enforcement (Issue #521).

DoD coverage:
  - [x] Missing korrekturgrund → HTTP 422 (korrekturgrund_required)
  - [x] Empty korrekturgrund string → HTTP 422 (korrekturgrund_required)
  - [x] Placeholder korrekturgrund (TODO/TBD/N/A/-) → HTTP 422
  - [x] Too-short korrekturgrund (< 10 chars) → HTTP 422
  - [x] Valid correction with all Pflichtfelder → HTTP 201 + version in response
  - [x] Document not found → HTTP 404
  - [x] Other invalid payload (bad version format) → HTTP 422
  - [x] Acceptance: "Speichern ohne Grund wird blockiert" — no store mutation on failure
"""

import unittest
from http import HTTPStatus

from src.api.compliance_corrections import handle_correction_request
from src.compliance.correction_workflow import CorrectionStore

_VALID_PAYLOAD = {
    "version": "v1.1",
    "supersedes_version": "v1.0",
    "korrekturgrund": "Pflichtfeldvalidierung ergänzt; unklare Freitextregel entfernt",
    "wirksam_ab": "2026-03-05",
    "approved_by_role": "Compliance Lead",
    "evidence_ref": "https://github.com/nimeob/geo-ranking-ch/issues/521",
}


def _store_with_doc(document_id: str = "POL-TEST-001") -> CorrectionStore:
    store = CorrectionStore()
    store.register(document_id, content={"text": "original"}, version="v1.0")
    return store


class TestKorrekturgrundEnforcementAtAPILayer(unittest.TestCase):
    """Acceptance test: Speichern ohne Grund wird blockiert."""

    def _call(self, payload: dict, document_id: str = "POL-TEST-001", store=None):
        if store is None:
            store = _store_with_doc(document_id)
        return handle_correction_request(
            document_id=document_id,
            payload=payload,
            request_id="test-req-001",
            store=store,
        )

    # ------------------------------------------------------------------ happy
    def test_valid_correction_returns_201(self):
        store = _store_with_doc()
        body, status = self._call(_VALID_PAYLOAD, store=store)
        self.assertEqual(status, HTTPStatus.CREATED)
        self.assertTrue(body["ok"])
        self.assertEqual(body["version"], "v1.1")
        self.assertEqual(body["supersedes_version"], "v1.0")

    def test_valid_correction_mutates_store(self):
        store = _store_with_doc()
        self._call(_VALID_PAYLOAD, store=store)
        doc = store.get_document("POL-TEST-001")
        self.assertEqual(doc.current_version, "v1.1")

    # ------------------------------------------------------------------ 422: korrekturgrund
    def test_missing_korrekturgrund_returns_422(self):
        payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "korrekturgrund"}
        body, status = self._call(payload)
        self.assertEqual(status, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"], "korrekturgrund_required")

    def test_empty_korrekturgrund_returns_422(self):
        body, status = self._call({**_VALID_PAYLOAD, "korrekturgrund": ""})
        self.assertEqual(status, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(body["error"], "korrekturgrund_required")

    def test_whitespace_only_korrekturgrund_returns_422(self):
        body, status = self._call({**_VALID_PAYLOAD, "korrekturgrund": "   "})
        self.assertEqual(status, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(body["error"], "korrekturgrund_required")

    def test_placeholder_todo_returns_422(self):
        body, status = self._call({**_VALID_PAYLOAD, "korrekturgrund": "TODO"})
        self.assertEqual(status, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(body["error"], "korrekturgrund_required")

    def test_placeholder_tbd_returns_422(self):
        body, status = self._call({**_VALID_PAYLOAD, "korrekturgrund": "tbd"})
        self.assertEqual(status, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(body["error"], "korrekturgrund_required")

    def test_placeholder_na_returns_422(self):
        body, status = self._call({**_VALID_PAYLOAD, "korrekturgrund": "N/A"})
        self.assertEqual(status, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(body["error"], "korrekturgrund_required")

    def test_placeholder_dash_returns_422(self):
        body, status = self._call({**_VALID_PAYLOAD, "korrekturgrund": "-"})
        self.assertEqual(status, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(body["error"], "korrekturgrund_required")

    def test_too_short_korrekturgrund_returns_422(self):
        # Under 10 characters
        body, status = self._call({**_VALID_PAYLOAD, "korrekturgrund": "kurz"})
        self.assertEqual(status, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(body["error"], "korrekturgrund_required")

    def test_non_string_korrekturgrund_returns_422(self):
        body, status = self._call({**_VALID_PAYLOAD, "korrekturgrund": 12345})
        self.assertEqual(status, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(body["error"], "korrekturgrund_required")

    # ------------------------------------------------------------------ no side-effect on failure
    def test_store_unchanged_on_korrekturgrund_missing(self):
        """Core DoD: failed save leaves store in original state."""
        store = _store_with_doc()
        payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "korrekturgrund"}
        self._call(payload, store=store)
        doc = store.get_document("POL-TEST-001")
        self.assertEqual(
            doc.current_version,
            "v1.0",
            "Store must remain at v1.0 after rejected save (no side effect)",
        )

    def test_store_unchanged_on_empty_korrekturgrund(self):
        store = _store_with_doc()
        self._call({**_VALID_PAYLOAD, "korrekturgrund": ""}, store=store)
        self.assertEqual(store.get_document("POL-TEST-001").current_version, "v1.0")

    # ------------------------------------------------------------------ 422: other payload errors
    def test_missing_required_field_version_returns_422(self):
        payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "version"}
        body, status = self._call(payload)
        self.assertEqual(status, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(body["error"], "invalid_correction_payload")

    def test_bad_version_format_returns_422(self):
        body, status = self._call({**_VALID_PAYLOAD, "version": "1.0"})
        self.assertEqual(status, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(body["error"], "invalid_correction_payload")

    def test_bad_evidence_ref_returns_422(self):
        body, status = self._call({**_VALID_PAYLOAD, "evidence_ref": "plaintext"})
        self.assertEqual(status, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(body["error"], "invalid_correction_payload")

    def test_non_dict_payload_returns_422(self):
        store = _store_with_doc()
        body, status = handle_correction_request(
            document_id="POL-TEST-001",
            payload="not a dict",  # type: ignore[arg-type]
            request_id="test-req-002",
            store=store,
        )
        self.assertEqual(status, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(body["error"], "invalid_correction_payload")

    # ------------------------------------------------------------------ 404
    def test_unknown_document_returns_404(self):
        store = CorrectionStore()  # empty store
        body, status = handle_correction_request(
            document_id="DOES-NOT-EXIST",
            payload=_VALID_PAYLOAD,
            request_id="test-req-003",
            store=store,
        )
        self.assertEqual(status, HTTPStatus.NOT_FOUND)
        self.assertEqual(body["error"], "document_not_found")

    # ------------------------------------------------------------------ request_id passthrough
    def test_request_id_in_error_response(self):
        payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "korrekturgrund"}
        store = _store_with_doc()
        body, _ = handle_correction_request(
            document_id="POL-TEST-001",
            payload=payload,
            request_id="trace-42",
            store=store,
        )
        self.assertEqual(body["request_id"], "trace-42")

    def test_request_id_in_success_response(self):
        store = _store_with_doc()
        body, _ = handle_correction_request(
            document_id="POL-TEST-001",
            payload=_VALID_PAYLOAD,
            request_id="trace-99",
            store=store,
        )
        self.assertEqual(body["request_id"], "trace-99")


if __name__ == "__main__":
    unittest.main()
