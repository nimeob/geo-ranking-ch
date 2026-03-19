from __future__ import annotations

import unittest

from src.api import address_intel


class TestAddressIntelReportSummary(unittest.TestCase):
    def test_source_catalog_view_keeps_policy_rank_and_optional_defaults(self):
        view = address_intel.source_catalog_view(
            {
                "geoadmin_gwr": {"status": "ok"},
                "google_news_rss": {"status": "error", "optional": False},
            }
        )

        self.assertEqual(view["geoadmin_gwr"]["status"], "ok")
        self.assertEqual(view["geoadmin_gwr"]["policy_rank"], address_intel.SOURCE_POLICY_RANK["official"])
        self.assertTrue(view["google_news_rss"]["optional"] is False)

    def test_build_field_provenance_marks_present_and_authority(self):
        provenance = address_intel.build_field_provenance(
            {
                "ids": {"egid": 123},
                "administrative": {"gemeinde": "St. Gallen"},
                "cross_source": {"elevation": {"height_m": 700}},
                "building": {"codes": {"gstat": 1004}, "decoded": {"status": "bestehend"}},
                "energy": {"raw_codes": {"gwaerzh1": 7430}, "heating_layer": "Fernwärme"},
                "intelligence": {
                    "tenants_businesses": {"entities": [{"name": "Café"}]},
                    "incidents_timeline": {"events": []},
                    "environment_noise_risk": {"score": 0.2},
                    "consistency_checks": {"status": "ok"},
                    "executive_risk_summary": {"traffic_light": "green"},
                },
                "suitability_light": {"score": 0.81, "traffic_light": "green"},
            }
        )

        self.assertTrue(provenance["ids.egid"]["present"])
        self.assertEqual(provenance["ids.egid"]["authority"], "official")
        self.assertFalse(provenance["cross_source.plz_layer.plz"]["present"])

    def test_build_executive_summary_switches_to_review_for_low_confidence(self):
        summary = address_intel.build_executive_summary(
            {
                "confidence": {
                    "level": "low",
                    "warnings": ["manual review"],
                    "ambiguity": {"level": "medium", "score_gap_to_next": 0.03},
                }
            }
        )

        self.assertEqual(summary["verdict"], "review")
        self.assertTrue(summary["needs_review"])
        self.assertEqual(summary["ambiguity_level"], "medium")
        self.assertEqual(summary["ambiguity_gap"], 0.03)
        self.assertEqual(summary["warnings"], ["manual review"])


if __name__ == "__main__":
    unittest.main()
