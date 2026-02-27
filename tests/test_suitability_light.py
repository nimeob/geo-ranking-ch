import unittest

from src.suitability_light import evaluate_suitability_light


class TestSuitabilityLightHeuristic(unittest.TestCase):
    def test_high_quality_case_is_green(self):
        result = evaluate_suitability_light(
            elevation_m=620,
            has_road_access=True,
            confidence_score=88,
            building_status="Bestehend",
            has_plz=True,
            has_admin_boundary=True,
        )

        self.assertEqual(result["traffic_light"], "green")
        self.assertGreaterEqual(result["score"], 72)
        self.assertEqual(result["uncertainty"]["level"], "low")
        self.assertEqual(result["status"], "ok")
        self.assertIn("base_score", result)
        self.assertIn("personalized_score", result)
        self.assertEqual(result["personalized_score"], result["base_score"])

    def test_missing_access_and_low_confidence_is_not_green(self):
        result = evaluate_suitability_light(
            elevation_m=1650,
            has_road_access=False,
            confidence_score=41,
            building_status="Geplant",
            has_plz=False,
            has_admin_boundary=False,
        )

        self.assertIn(result["traffic_light"], {"yellow", "red"})
        self.assertGreaterEqual(result["uncertainty"]["score"], 25)
        self.assertTrue(any("Erschliessung" in row for row in result["limitations"]))

    def test_missing_inputs_raise_uncertainty_and_keep_determinism(self):
        first = evaluate_suitability_light(
            elevation_m=None,
            has_road_access=False,
            confidence_score=None,
            building_status=None,
            has_plz=True,
            has_admin_boundary=False,
        )
        second = evaluate_suitability_light(
            elevation_m=None,
            has_road_access=False,
            confidence_score=None,
            building_status=None,
            has_plz=True,
            has_admin_boundary=False,
        )

        self.assertEqual(first, second)
        self.assertEqual(first["heuristic_version"], "bl-20.5.b-v1")
        self.assertGreaterEqual(first["uncertainty"]["score"], 40)
        self.assertGreaterEqual(len(first["factors"]), 4)
        self.assertEqual(first["personalized_score"], first["base_score"])


if __name__ == "__main__":
    unittest.main()
