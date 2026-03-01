"""Tests for src/compliance/correction_workflow.py  (Issue #520).

DoD coverage:
  - [x] Original bleibt unverändert — Überschreiben unmöglich (technischer Test)
  - [x] Neue Korrekturversion wird korrekt erstellt
  - [x] Pflichtfelder werden erzwungen (version, supersedes_version, korrekturgrund,
        wirksam_ab, approved_by_role, evidence_ref)
  - [x] Placeholder-/Leerfeld-Ablehnung für korrekturgrund
  - [x] version == supersedes_version wird abgelehnt
  - [x] Doppelte version-Registrierung (Overwrite-Guard) wird abgelehnt
  - [x] Mehrere Korrekturen in Folge (lineare Versionshistorie)
  - [x] get_version() liefert Original jederzeit abrufbar
"""

import unittest
from datetime import date, timedelta

from src.compliance.correction_workflow import (
    CorrectionMetadataV1,
    CorrectionStore,
    VersionedDocument,
)

_BASE_CORRECTION = {
    "version": "v1.1",
    "supersedes_version": "v1.0",
    "korrekturgrund": "Abschnitt zu Pflichtfeldvalidierung präzisiert; unklare Freitextregel entfernt",
    "wirksam_ab": "2026-03-05",
    "approved_by_role": "Compliance Lead",
    "evidence_ref": "https://github.com/nimeob/geo-ranking-ch/issues/520",
}


def _store_with_doc(document_id: str = "POL-001") -> CorrectionStore:
    store = CorrectionStore()
    store.register(document_id, content={"text": "original content v1.0"}, version="v1.0")
    return store


class TestCorrectionMetadataV1Validation(unittest.TestCase):
    # ----- happy path -----
    def test_valid_payload_parses_correctly(self):
        m = CorrectionMetadataV1.from_dict(_BASE_CORRECTION)
        self.assertEqual(m.version, "v1.1")
        self.assertEqual(m.supersedes_version, "v1.0")
        self.assertEqual(m.wirksam_ab, date(2026, 3, 5))
        self.assertEqual(m.approved_by_role, "Compliance Lead")
        self.assertTrue(m.evidence_ref.startswith("https://"))

    def test_to_dict_round_trip(self):
        m = CorrectionMetadataV1.from_dict(_BASE_CORRECTION)
        d = m.to_dict()
        self.assertEqual(d["version"], "v1.1")
        self.assertEqual(d["wirksam_ab"], "2026-03-05")

    def test_evidence_ref_hash_prefix(self):
        payload = {**_BASE_CORRECTION, "evidence_ref": "#520"}
        m = CorrectionMetadataV1.from_dict(payload)
        self.assertTrue(m.evidence_ref.startswith("#"))

    def test_evidence_ref_issue_prefix(self):
        payload = {**_BASE_CORRECTION, "evidence_ref": "issue:520"}
        m = CorrectionMetadataV1.from_dict(payload)
        self.assertTrue(m.evidence_ref.startswith("issue:"))

    # ----- missing fields -----
    def test_missing_any_required_field_raises(self):
        for key in _BASE_CORRECTION:
            payload = {k: v for k, v in _BASE_CORRECTION.items() if k != key}
            with self.subTest(missing=key):
                with self.assertRaises(ValueError):
                    CorrectionMetadataV1.from_dict(payload)

    # ----- bad version formats -----
    def test_invalid_version_format_raises(self):
        for bad in ("1.0", "v1", "v1.0.1", "", "v1.x"):
            with self.subTest(version=bad):
                with self.assertRaises(ValueError):
                    CorrectionMetadataV1.from_dict({**_BASE_CORRECTION, "version": bad})

    def test_invalid_supersedes_version_format_raises(self):
        payload = {**_BASE_CORRECTION, "supersedes_version": "1.0"}
        with self.assertRaises(ValueError):
            CorrectionMetadataV1.from_dict(payload)

    def test_version_equals_supersedes_version_raises(self):
        payload = {**_BASE_CORRECTION, "version": "v1.0", "supersedes_version": "v1.0"}
        with self.assertRaises(ValueError):
            CorrectionMetadataV1.from_dict(payload)

    # ----- korrekturgrund quality -----
    def test_empty_korrekturgrund_raises(self):
        with self.assertRaises(ValueError):
            CorrectionMetadataV1.from_dict({**_BASE_CORRECTION, "korrekturgrund": ""})

    def test_placeholder_korrekturgrund_todo_raises(self):
        for placeholder in ("TODO", "todo", "TBD", "tbd", "N/A", "n/a", "-"):
            with self.subTest(placeholder=placeholder):
                with self.assertRaises(ValueError):
                    CorrectionMetadataV1.from_dict(
                        {**_BASE_CORRECTION, "korrekturgrund": placeholder}
                    )

    def test_too_short_korrekturgrund_raises(self):
        # Under 10 characters
        with self.assertRaises(ValueError):
            CorrectionMetadataV1.from_dict(
                {**_BASE_CORRECTION, "korrekturgrund": "kurz"}
            )

    # ----- wirksam_ab -----
    def test_invalid_wirksam_ab_raises(self):
        with self.assertRaises(ValueError):
            CorrectionMetadataV1.from_dict({**_BASE_CORRECTION, "wirksam_ab": "2026-13-01"})

    def test_non_string_wirksam_ab_raises(self):
        with self.assertRaises(ValueError):
            CorrectionMetadataV1.from_dict({**_BASE_CORRECTION, "wirksam_ab": 20260305})

    # ----- evidence_ref -----
    def test_invalid_evidence_ref_raises(self):
        with self.assertRaises(ValueError):
            CorrectionMetadataV1.from_dict({**_BASE_CORRECTION, "evidence_ref": "plaintext"})


class TestOriginalImmutabilityInVersionedDocument(unittest.TestCase):
    """Technical proof that overwriting the original is impossible."""

    def _make_doc(self) -> VersionedDocument:
        return VersionedDocument(
            document_id="POL-001",
            content={"text": "original"},
            version="v1.0",
        )

    def test_original_accessible_after_correction(self):
        doc = self._make_doc()
        correction = CorrectionMetadataV1.from_dict(_BASE_CORRECTION)
        doc.apply_correction(correction, {"text": "corrected v1.1"})

        # Original must still be retrievable
        original = doc.get_version("v1.0")
        self.assertEqual(original, {"text": "original"})

    def test_overwriting_existing_version_is_impossible(self):
        """Applying a correction whose version already exists in history raises."""
        doc = self._make_doc()

        # Apply first correction: v1.0 → v1.1
        correction = CorrectionMetadataV1.from_dict(_BASE_CORRECTION)
        doc.apply_correction(correction, {"text": "first correction"})

        # Apply second correction: v1.1 → v1.2  (so current = v1.2)
        correction2 = CorrectionMetadataV1.from_dict(
            {
                "version": "v1.2",
                "supersedes_version": "v1.1",
                "korrekturgrund": "Zweite Korrektur: weiterer Abschnitt präzisiert",
                "wirksam_ab": "2026-03-06",
                "approved_by_role": "Compliance Lead",
                "evidence_ref": "#520",
            }
        )
        doc.apply_correction(correction2, {"text": "second correction"})

        # Now try to apply a correction that (re)uses version v1.1 — already in history.
        # Use a direct CorrectionMetadataV1 constructor to bypass from_dict guards.
        duplicate_of_v1_1 = CorrectionMetadataV1(
            version="v1.1",           # already exists in history
            supersedes_version="v1.2",  # correct supersedes for current
            korrekturgrund="Überschreibversuch — v1.1 soll scheitern weil bereits vorhanden",
            wirksam_ab=date(2026, 3, 7),
            approved_by_role="Compliance Lead",
            evidence_ref="#520",
        )
        with self.assertRaises(ValueError, msg="Re-using an existing version must be rejected"):
            doc.apply_correction(duplicate_of_v1_1, {"text": "OVERWRITE ATTEMPT"})

    def test_history_is_append_only(self):
        doc = self._make_doc()
        original_history_id = id(doc._history[0])

        correction = CorrectionMetadataV1.from_dict(_BASE_CORRECTION)
        doc.apply_correction(correction, {"text": "corrected"})

        # First entry (original) must be the same object — never replaced
        self.assertEqual(id(doc._history[0]), original_history_id)
        self.assertEqual(len(doc.all_versions()), 2)

    def test_multiple_corrections_build_linear_history(self):
        doc = self._make_doc()

        for i, (new_ver, sup_ver) in enumerate(
            [("v1.1", "v1.0"), ("v1.2", "v1.1"), ("v2.0", "v1.2")]
        ):
            correction = CorrectionMetadataV1.from_dict(
                {
                    "version": new_ver,
                    "supersedes_version": sup_ver,
                    "korrekturgrund": f"Korrektur Iteration {i + 1}: sachliche Präzisierung",
                    "wirksam_ab": (date(2026, 3, 5) + timedelta(days=i)).isoformat(),
                    "approved_by_role": "Compliance Lead",
                    "evidence_ref": "#520",
                }
            )
            doc.apply_correction(correction, {"text": f"content {new_ver}"})

        versions = doc.all_versions()
        self.assertEqual(versions, ["v1.0", "v1.1", "v1.2", "v2.0"])
        # Original must still be the original
        self.assertEqual(doc.get_version("v1.0"), {"text": "original"})
        # Current must be latest
        self.assertEqual(doc.current_version, "v2.0")

    def test_supersedes_wrong_version_raises(self):
        doc = self._make_doc()
        # Current version is v1.0; trying to supersede v1.1 (non-existent) must fail
        correction = CorrectionMetadataV1.from_dict(
            {**_BASE_CORRECTION, "supersedes_version": "v1.1", "version": "v1.2"}
        )
        with self.assertRaises(ValueError):
            doc.apply_correction(correction, {"text": "bad correction"})


class TestCorrectionStore(unittest.TestCase):
    def test_register_and_retrieve_document(self):
        store = _store_with_doc()
        doc = store.get_document("POL-001")
        self.assertEqual(doc.version, "v1.0")
        self.assertEqual(store.original_content("POL-001"), {"text": "original content v1.0"})

    def test_register_duplicate_id_raises(self):
        store = _store_with_doc()
        with self.assertRaises(ValueError):
            store.register("POL-001", content={"text": "duplicate"}, version="v1.0")

    def test_apply_correction_creates_new_version(self):
        store = _store_with_doc()
        store.apply_correction(
            "POL-001",
            _BASE_CORRECTION,
            new_content={"text": "corrected content v1.1"},
        )
        doc = store.get_document("POL-001")
        self.assertEqual(doc.current_version, "v1.1")
        self.assertEqual(doc.current_content, {"text": "corrected content v1.1"})

    def test_original_unchanged_after_correction(self):
        store = _store_with_doc()
        store.apply_correction("POL-001", _BASE_CORRECTION, new_content={"text": "v1.1"})
        self.assertEqual(
            store.original_content("POL-001"),
            {"text": "original content v1.0"},
            "Original must be immutable after correction",
        )

    def test_invalid_correction_payload_raises_without_side_effects(self):
        store = _store_with_doc()
        bad_payload = {**_BASE_CORRECTION, "korrekturgrund": ""}
        with self.assertRaises(ValueError):
            store.apply_correction("POL-001", bad_payload, new_content={"text": "bad"})
        # Store should be unchanged
        doc = store.get_document("POL-001")
        self.assertEqual(doc.current_version, "v1.0")

    def test_get_nonexistent_document_raises(self):
        store = CorrectionStore()
        with self.assertRaises(KeyError):
            store.get_document("UNKNOWN")

    def test_multiple_independent_documents(self):
        store = CorrectionStore()
        store.register("POL-001", {"text": "a"}, "v1.0")
        store.register("POL-002", {"text": "b"}, "v1.0")
        store.apply_correction("POL-001", _BASE_CORRECTION, {"text": "a corrected"})
        # POL-002 must be unaffected
        self.assertEqual(store.get_document("POL-002").current_version, "v1.0")
        self.assertEqual(store.original_content("POL-002"), {"text": "b"})


if __name__ == "__main__":
    unittest.main()
