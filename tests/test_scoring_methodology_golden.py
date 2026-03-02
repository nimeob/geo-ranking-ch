import json
import re
import unittest
from pathlib import Path

from src.personalized_scoring import compute_two_stage_scores


REPO_ROOT = Path(__file__).resolve().parents[1]
SCORING_METHODOLOGY_DOC = REPO_ROOT / "docs" / "api" / "scoring_methodology.md"
SCORING_WORKED_EXAMPLES_DIR = REPO_ROOT / "docs" / "api" / "examples" / "scoring"
EXPLAINABILITY_E2E_EXAMPLES_DIR = REPO_ROOT / "docs" / "api" / "examples" / "explainability"

EXPECTED_GOLDEN = {
    "worked-example-01-high-confidence": {
        "score": 91,
        "level": "high",
        "legacy_confidence": 0.91,
        "selected_score": 0.96,
        "noise_risk": "low",
    },
    "worked-example-02-medium-confidence": {
        "score": 65,
        "level": "medium",
        "legacy_confidence": 0.65,
        "selected_score": 0.74,
        "noise_risk": "medium",
    },
    "worked-example-03-low-confidence": {
        "score": 34,
        "level": "low",
        "legacy_confidence": 0.34,
        "selected_score": 0.51,
        "noise_risk": "high",
    },
    "worked-example-04-threshold-high": {
        "score": 82,
        "level": "high",
        "legacy_confidence": 0.82,
        "selected_score": 0.9,
        "noise_risk": "low",
    },
    "worked-example-05-threshold-medium": {
        "score": 81,
        "level": "medium",
        "legacy_confidence": 0.81,
        "selected_score": 0.87,
        "noise_risk": "medium",
    },
    "worked-example-06-threshold-medium-floor": {
        "score": 62,
        "level": "medium",
        "legacy_confidence": 0.62,
        "selected_score": 0.7,
        "noise_risk": "medium",
    },
    "worked-example-07-threshold-low-ceil": {
        "score": 61,
        "level": "low",
        "legacy_confidence": 0.61,
        "selected_score": 0.7,
        "noise_risk": "high",
    },
    "worked-example-08-clamp-zero": {
        "score": 0,
        "level": "low",
        "legacy_confidence": 0.0,
        "selected_score": 0.2,
        "noise_risk": "high",
    },
    "worked-example-09-max-score": {
        "score": 100,
        "level": "high",
        "legacy_confidence": 1.0,
        "selected_score": 1.0,
        "noise_risk": "low",
    },
    "worked-example-10-mismatch-heavy": {
        "score": 74,
        "level": "medium",
        "legacy_confidence": 0.74,
        "selected_score": 0.9,
        "noise_risk": "high",
    },
    "worked-example-11-ambiguity-heavy": {
        "score": 58,
        "level": "low",
        "legacy_confidence": 0.58,
        "selected_score": 0.75,
        "noise_risk": "medium",
    },
}

EXPLAINABILITY_E2E_CASES = {
    "explainability-e2e-01-quiet-first": {
        "delta_sign": -1,
        "profile": "quiet-first",
    },
    "explainability-e2e-02-urban-first": {
        "delta_sign": 1,
        "profile": "urban-first",
    },
}

PERSONALIZED_RUNTIME_GOLDEN_CASES = {
    "personalized-golden-01-quiet-first": {
        "delta_sign": 1,
        "profile": "quiet-first",
    },
    "personalized-golden-02-urban-first": {
        "delta_sign": -1,
        "profile": "urban-first",
    },
}

REQUIRED_EXPLAINABILITY_FACTOR_KEYS = {
    "key",
    "raw_value",
    "normalized",
    "weight",
    "contribution",
    "direction",
    "reason",
    "source",
}


class TestScoringMethodologyGolden(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc_content = SCORING_METHODOLOGY_DOC.read_text(encoding="utf-8")

        match = re.search(r"Methodik-Version:\s*`([^`]+)`", cls.doc_content)
        if not match:
            raise AssertionError("Methodik-Version nicht in docs/api/scoring_methodology.md gefunden")
        cls.methodology_version = match.group(1)

    def test_versioning_and_migration_rules_are_documented(self):
        markers = [
            "## 9) Methodik-Versionierung und Migrationsregeln",
            "Patch",
            "Minor",
            "Major",
            "Golden-Tests",
            "Migrationshinweise",
        ]
        for marker in markers:
            self.assertIn(marker, self.doc_content, msg=f"Marker fehlt in scoring_methodology.md: {marker}")

    def test_two_stage_scoring_matrix_and_fallback_are_documented(self):
        markers = [
            "### 2.3.2 Zweistufiges Scoring + Präferenzmatrix (BL-20.4.d)",
            "compute_two_stage_scores",
            "personalized_score == base_score",
            "fallback_applied = true",
            "weights.base",
            "weights.personalized",
            "weights.delta",
            "signal_strength",
            "lifestyle_density",
            "noise_tolerance",
            "nightlife_preference",
            "school_proximity",
            "family_friendly_focus",
            "commute_priority",
        ]
        for marker in markers:
            self.assertIn(marker, self.doc_content, msg=f"Marker fehlt in scoring_methodology.md: {marker}")

    def test_worked_examples_are_version_pinned_to_methodology(self):
        self.assertTrue(EXPECTED_GOLDEN, msg="Keine Golden-Referenzfälle definiert")

        for case in EXPECTED_GOLDEN:
            input_path = SCORING_WORKED_EXAMPLES_DIR / f"{case}.input.json"
            output_path = SCORING_WORKED_EXAMPLES_DIR / f"{case}.output.json"

            self.assertTrue(input_path.is_file(), msg=f"Fehlendes Input-Artefakt: {input_path}")
            self.assertTrue(output_path.is_file(), msg=f"Fehlendes Output-Artefakt: {output_path}")

            input_payload = json.loads(input_path.read_text(encoding="utf-8"))
            output_payload = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(
                input_payload.get("methodology_version"),
                self.methodology_version,
                msg=f"Input-Version stimmt nicht mit Methodik-Version überein: {case}",
            )
            self.assertEqual(
                output_payload.get("methodology_version"),
                self.methodology_version,
                msg=f"Output-Version stimmt nicht mit Methodik-Version überein: {case}",
            )

    def test_golden_reference_scores_are_stable(self):
        for case, expected in EXPECTED_GOLDEN.items():
            output_path = SCORING_WORKED_EXAMPLES_DIR / f"{case}.output.json"
            payload = json.loads(output_path.read_text(encoding="utf-8"))

            confidence = payload.get("result_projection", {}).get("status", {}).get("quality", {}).get("confidence", {})
            selected_score = (
                payload.get("result_projection", {})
                .get("data", {})
                .get("modules", {})
                .get("match", {})
                .get("selected_score")
            )
            legacy_confidence = payload.get("result_projection", {}).get("confidence")
            noise_risk = payload.get("result_projection", {}).get("context_profile", {}).get("noise_risk")

            self.assertEqual(
                confidence.get("score"),
                expected["score"],
                msg=f"Score-Drift erkannt für {case}",
            )
            self.assertEqual(
                confidence.get("level"),
                expected["level"],
                msg=f"Level-Drift erkannt für {case}",
            )
            self.assertEqual(
                legacy_confidence,
                expected["legacy_confidence"],
                msg=f"Legacy-Confidence-Drift erkannt für {case}",
            )
            self.assertEqual(
                selected_score,
                expected["selected_score"],
                msg=f"Match-Selected-Score-Drift erkannt für {case}",
            )
            self.assertEqual(
                noise_risk,
                expected["noise_risk"],
                msg=f"Noise-Risk-Drift erkannt für {case}",
            )

    def test_explainability_e2e_examples_are_linked_from_methodology(self):
        for case in EXPLAINABILITY_E2E_CASES:
            input_rel = f"./examples/explainability/{case}.input.json"
            output_rel = f"./examples/explainability/{case}.output.json"
            self.assertIn(input_rel, self.doc_content, msg=f"Input-Link fehlt in Methodik-Doku: {input_rel}")
            self.assertIn(output_rel, self.doc_content, msg=f"Output-Link fehlt in Methodik-Doku: {output_rel}")

    def test_explainability_e2e_examples_have_required_factors(self):
        for case, meta in EXPLAINABILITY_E2E_CASES.items():
            input_path = EXPLAINABILITY_E2E_EXAMPLES_DIR / f"{case}.input.json"
            output_path = EXPLAINABILITY_E2E_EXAMPLES_DIR / f"{case}.output.json"

            self.assertTrue(input_path.is_file(), msg=f"Fehlendes Input-Artefakt: {input_path}")
            self.assertTrue(output_path.is_file(), msg=f"Fehlendes Output-Artefakt: {output_path}")

            input_payload = json.loads(input_path.read_text(encoding="utf-8"))
            output_payload = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(
                input_payload.get("methodology_version"),
                self.methodology_version,
                msg=f"Input-Version stimmt nicht mit Methodik-Version überein: {case}",
            )
            self.assertEqual(
                output_payload.get("methodology_version"),
                self.methodology_version,
                msg=f"Output-Version stimmt nicht mit Methodik-Version überein: {case}",
            )

            personalized_profile = (
                output_payload.get("result_projection", {})
                .get("explainability", {})
                .get("personalized", {})
                .get("profile")
            )
            self.assertEqual(
                personalized_profile,
                meta["profile"],
                msg=f"Unerwartetes Personalized-Profil in {case}",
            )

            base_factors = (
                output_payload.get("result_projection", {})
                .get("explainability", {})
                .get("base", {})
                .get("factors", [])
            )
            personalized_factors = (
                output_payload.get("result_projection", {})
                .get("explainability", {})
                .get("personalized", {})
                .get("factors", [])
            )

            self.assertGreaterEqual(len(base_factors), 4, msg=f"Zu wenige Base-Faktoren in {case}")
            self.assertGreaterEqual(
                len(personalized_factors),
                4,
                msg=f"Zu wenige Personalized-Faktoren in {case}",
            )

            for factor in base_factors + personalized_factors:
                missing = REQUIRED_EXPLAINABILITY_FACTOR_KEYS - set(factor.keys())
                self.assertFalse(missing, msg=f"Faktor in {case} unvollständig, fehlend: {sorted(missing)}")

    def test_explainability_e2e_examples_show_personalization_delta(self):
        for case, meta in EXPLAINABILITY_E2E_CASES.items():
            output_path = EXPLAINABILITY_E2E_EXAMPLES_DIR / f"{case}.output.json"
            output_payload = json.loads(output_path.read_text(encoding="utf-8"))

            delta = output_payload.get("annotations", {}).get("personalized_minus_base")
            self.assertIsInstance(delta, (int, float), msg=f"Delta fehlt oder ungültig in {case}")

            if meta["delta_sign"] < 0:
                self.assertLess(delta, 0, msg=f"Erwarteter negativer Profil-Effekt fehlt in {case}")
            else:
                self.assertGreater(delta, 0, msg=f"Erwarteter positiver Profil-Effekt fehlt in {case}")

            base_by_key = {
                item["key"]: item
                for item in output_payload.get("result_projection", {})
                .get("explainability", {})
                .get("base", {})
                .get("factors", [])
            }
            personalized_by_key = {
                item["key"]: item
                for item in output_payload.get("result_projection", {})
                .get("explainability", {})
                .get("personalized", {})
                .get("factors", [])
            }
            shared_keys = set(base_by_key) & set(personalized_by_key)
            direction_flips = [
                key
                for key in shared_keys
                if base_by_key[key].get("direction") != personalized_by_key[key].get("direction")
            ]
            self.assertTrue(
                direction_flips,
                msg=f"Mindestens ein Richtungswechsel pro Beispiel erwartet (pro/contra): {case}",
            )

    def test_personalized_runtime_golden_examples_are_linked_from_methodology(self):
        for case in PERSONALIZED_RUNTIME_GOLDEN_CASES:
            input_rel = f"./examples/scoring/{case}.input.json"
            output_rel = f"./examples/scoring/{case}.output.json"
            self.assertIn(input_rel, self.doc_content, msg=f"Input-Link fehlt in Methodik-Doku: {input_rel}")
            self.assertIn(output_rel, self.doc_content, msg=f"Output-Link fehlt in Methodik-Doku: {output_rel}")

    def test_personalized_runtime_golden_examples_are_deterministic_and_stable(self):
        deltas: list[float] = []

        for case, meta in PERSONALIZED_RUNTIME_GOLDEN_CASES.items():
            input_path = SCORING_WORKED_EXAMPLES_DIR / f"{case}.input.json"
            output_path = SCORING_WORKED_EXAMPLES_DIR / f"{case}.output.json"

            self.assertTrue(input_path.is_file(), msg=f"Fehlendes Input-Artefakt: {input_path}")
            self.assertTrue(output_path.is_file(), msg=f"Fehlendes Output-Artefakt: {output_path}")

            input_payload = json.loads(input_path.read_text(encoding="utf-8"))
            output_payload = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(
                input_payload.get("methodology_version"),
                self.methodology_version,
                msg=f"Input-Version stimmt nicht mit Methodik-Version überein: {case}",
            )
            self.assertEqual(
                output_payload.get("methodology_version"),
                self.methodology_version,
                msg=f"Output-Version stimmt nicht mit Methodik-Version überein: {case}",
            )
            self.assertEqual(
                output_payload.get("profile"),
                meta["profile"],
                msg=f"Unerwartetes Profil im Output-Artefakt: {case}",
            )

            factors = input_payload.get("factors", [])
            preferences = input_payload.get("preferences", {})
            first = compute_two_stage_scores(factors, preferences)
            second = compute_two_stage_scores(factors, preferences)
            self.assertEqual(first, second, msg=f"Nicht-deterministischer Runtime-Output in {case}")

            expected_engine_output = output_payload.get("engine_output")
            self.assertEqual(first, expected_engine_output, msg=f"Golden-Drift erkannt für {case}")

            delta = round(first["personalized_score"] - first["base_score"], 4)
            deltas.append(delta)
            self.assertEqual(
                delta,
                output_payload.get("annotations", {}).get("personalized_minus_base"),
                msg=f"Delta-Artefakt stimmt nicht mit Runtime-Berechnung überein: {case}",
            )

            if meta["delta_sign"] < 0:
                self.assertLess(delta, 0, msg=f"Erwarteter negativer Profil-Effekt fehlt in {case}")
            else:
                self.assertGreater(delta, 0, msg=f"Erwarteter positiver Profil-Effekt fehlt in {case}")

        self.assertTrue(any(delta > 0 for delta in deltas), msg="Mindestens ein positiver Delta-Effekt erwartet")
        self.assertTrue(any(delta < 0 for delta in deltas), msg="Mindestens ein negativer Delta-Effekt erwartet")


if __name__ == "__main__":
    unittest.main()
