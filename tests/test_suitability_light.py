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

        self.assertIn("top_factors", result)
        self.assertIsInstance(result["top_factors"], list)
        self.assertLessEqual(len(result["top_factors"]), 5)
        self.assertEqual(
            [row.get("key") for row in result["top_factors"]],
            ["topography", "access", "data_quality", "building_state"],
        )

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

        top_factors = result.get("top_factors")
        self.assertIsInstance(top_factors, list)
        self.assertLessEqual(len(top_factors), 5)
        self.assertEqual(
            [row.get("key") for row in top_factors],
            ["access", "topography", "data_quality", "building_state"],
        )
        self.assertTrue(all(float(row.get("contribution") or 0.0) <= 0 for row in top_factors))

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
        self.assertIn("top_factors", first)
        self.assertIsInstance(first["top_factors"], list)
        self.assertLessEqual(len(first["top_factors"]), 5)


if __name__ == "__main__":
    unittest.main()
