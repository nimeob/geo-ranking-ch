import unittest

from src.personalized_scoring import compute_two_stage_scores


class TestPersonalizedScoringEngine(unittest.TestCase):
    def setUp(self):
        self.factors = [
            {"key": "topography", "score": 82.0, "weight": 0.34},
            {"key": "access", "score": 76.0, "weight": 0.29},
            {"key": "building_state", "score": 74.0, "weight": 0.17},
            {"key": "data_quality", "score": 88.0, "weight": 0.20},
        ]

    def test_fallback_without_preferences_keeps_scores_identical(self):
        result = compute_two_stage_scores(self.factors, preferences=None)
        self.assertTrue(result["fallback_applied"])
        self.assertEqual(result["base_score"], result["personalized_score"])

    def test_result_is_deterministic_for_same_input(self):
        preferences = {
            "lifestyle_density": "urban",
            "noise_tolerance": "low",
            "nightlife_preference": "prefer",
            "school_proximity": "neutral",
            "family_friendly_focus": "medium",
            "commute_priority": "pt",
            "weights": {
                "commute_priority": 0.8,
                "noise_tolerance": 0.7,
            },
        }

        first = compute_two_stage_scores(self.factors, preferences=preferences)
        second = compute_two_stage_scores(self.factors, preferences=preferences)

        self.assertEqual(first, second)
        self.assertFalse(first["fallback_applied"])
        self.assertGreater(first["signal_strength"], 0.0)

    def test_contrasting_profiles_change_personalized_score_direction(self):
        quiet_profile = {
            "lifestyle_density": "rural",
            "noise_tolerance": "low",
            "nightlife_preference": "avoid",
            "school_proximity": "prefer",
            "family_friendly_focus": "high",
            "commute_priority": "car",
        }
        urban_profile = {
            "lifestyle_density": "urban",
            "noise_tolerance": "high",
            "nightlife_preference": "prefer",
            "school_proximity": "avoid",
            "family_friendly_focus": "low",
            "commute_priority": "pt",
        }

        quiet = compute_two_stage_scores(self.factors, preferences=quiet_profile)
        urban = compute_two_stage_scores(self.factors, preferences=urban_profile)

        self.assertNotEqual(quiet["personalized_score"], urban["personalized_score"])
        self.assertFalse(quiet["fallback_applied"])
        self.assertFalse(urban["fallback_applied"])

    def test_weight_normalization_preserves_total_weight(self):
        preferences = {
            "lifestyle_density": "urban",
            "commute_priority": "pt",
            "weights": {
                "lifestyle_density": 1.0,
                "commute_priority": 1.0,
            },
        }
        result = compute_two_stage_scores(self.factors, preferences=preferences)
        base_sum = sum(result["weights"]["base"].values())
        personalized_sum = sum(result["weights"]["personalized"].values())

        self.assertAlmostEqual(base_sum, personalized_sum, places=6)

    def test_zero_intensity_weights_trigger_fallback(self):
        preferences = {
            "lifestyle_density": "urban",
            "noise_tolerance": "low",
            "weights": {
                "lifestyle_density": 0.0,
                "noise_tolerance": 0.0,
            },
        }

        result = compute_two_stage_scores(self.factors, preferences=preferences)

        self.assertTrue(result["fallback_applied"])
        self.assertEqual(result["base_score"], result["personalized_score"])
        self.assertEqual(result["signal_strength"], 0.0)


if __name__ == "__main__":
    unittest.main()
