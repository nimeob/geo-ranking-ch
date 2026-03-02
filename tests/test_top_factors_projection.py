import unittest

from src.api.web_service import _apply_personalized_suitability_scores


class TestTopFactorsProjection(unittest.TestCase):
    def test_apply_personalization_derives_top_factors_for_report_and_compact_summary(self):
        report = {
            "suitability_light": {
                "status": "ok",
                "base_score": 80.1,
                "personalized_score": 80.1,
                "factors": [
                    {"key": "topography", "label": "Topografie", "score": 82.0, "weight": 0.34},
                    {"key": "access", "label": "Zugang", "score": 76.0, "weight": 0.29},
                    {"key": "building_state", "label": "Gebäude", "score": 74.0, "weight": 0.17},
                    {"key": "data_quality", "label": "Qualität", "score": 88.0, "weight": 0.20},
                ],
            },
            "summary_compact": {
                "suitability_light": {
                    "status": "ok",
                    "score": 80,
                    "traffic_light": "green",
                    "classification": "geeignet",
                }
            },
        }

        _apply_personalized_suitability_scores(report, preferences=None, preferences_supplied=False)

        suitability = report.get("suitability_light") or {}
        top_factors = suitability.get("top_factors")
        self.assertIsInstance(top_factors, list)
        self.assertLessEqual(len(top_factors), 5)
        self.assertTrue(top_factors, msg="top_factors must not be empty when factors are present")

        for row in top_factors:
            self.assertIsInstance(row, dict)
            self.assertIsInstance(row.get("key"), str)
            self.assertIsInstance(row.get("name"), str)
            self.assertIsInstance(row.get("contribution"), float)

        self.assertEqual(
            [row.get("key") for row in top_factors],
            ["topography", "data_quality", "access", "building_state"],
        )

        compact = report.get("summary_compact", {}).get("suitability_light", {})
        self.assertEqual(compact.get("top_factors"), top_factors)


if __name__ == "__main__":
    unittest.main()
