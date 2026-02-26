import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCORING_METHODOLOGY_DOC = REPO_ROOT / "docs" / "api" / "scoring_methodology.md"
SCORING_WORKED_EXAMPLES_DIR = REPO_ROOT / "docs" / "api" / "examples" / "scoring"

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


if __name__ == "__main__":
    unittest.main()
