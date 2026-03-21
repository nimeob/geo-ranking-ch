import importlib
import unittest


web_service = importlib.import_module("src.api.web_service")


class TestWebServiceOptionExtractors(unittest.TestCase):
    def test_query_param_resolvers_cover_history_and_notifications(self):
        self.assertEqual(web_service._resolve_result_projection_mode("requested"), "requested")
        self.assertEqual(web_service._resolve_notification_channel(" EMAIL "), "email")
        self.assertEqual(web_service._resolve_notification_limit("999"), 200)
        self.assertEqual(web_service._resolve_history_limit(None), 50)
        self.assertEqual(web_service._resolve_history_offset("12"), 12)

        with self.assertRaisesRegex(ValueError, "view must be one of"):
            web_service._resolve_result_projection_mode("legacy")
        with self.assertRaisesRegex(ValueError, "channel must be one of"):
            web_service._resolve_notification_channel("sms")
        with self.assertRaisesRegex(ValueError, "limit must be an integer >= 1"):
            web_service._resolve_notification_limit("0")
        with self.assertRaisesRegex(ValueError, "offset must be a non-negative integer"):
            web_service._resolve_history_offset("-1")

    def test_extract_request_options_rejects_non_object(self):
        with self.assertRaisesRegex(ValueError, "options must be an object"):
            web_service._extract_request_options({"options": []})

    def test_extract_async_mode_request_uses_shared_object_and_bool_validation(self):
        self.assertTrue(
            web_service._extract_async_mode_request({"async_mode": {"requested": True}})
        )
        with self.assertRaisesRegex(ValueError, "options.async_mode must be an object"):
            web_service._extract_async_mode_request({"async_mode": []})
        with self.assertRaisesRegex(ValueError, "options.async_mode.requested must be a boolean"):
            web_service._extract_async_mode_request({"async_mode": {"requested": "yes"}})

    def test_extract_deep_mode_request_uses_shared_helpers(self):
        result = web_service._extract_deep_mode_request(
            {
                "capabilities": {"deep_mode": {"requested": True, "profile": "Analysis_Plus", "max_budget_tokens": 500}},
                "entitlements": {"deep_mode": {"allowed": True, "quota_remaining": 7}},
            },
            intelligence_mode="extended",
        )

        self.assertEqual(
            result,
            {
                "requested": True,
                "profile": "analysis_plus",
                "allowed": True,
                "quota_remaining": 7,
                "max_budget_tokens": 500,
            },
        )

    def test_extract_deep_mode_request_rejects_invalid_nested_shapes(self):
        with self.assertRaisesRegex(ValueError, "options.capabilities.deep_mode must be an object"):
            web_service._extract_deep_mode_request(
                {"capabilities": {"deep_mode": []}},
                intelligence_mode="basic",
            )

        with self.assertRaisesRegex(ValueError, "options.entitlements.deep_mode.allowed must be a boolean"):
            web_service._extract_deep_mode_request(
                {"entitlements": {"deep_mode": {"allowed": "true"}}},
                intelligence_mode="basic",
            )

    def test_resolve_intelligence_mode_supports_legacy_level_values(self):
        extended_mode, extended_source = web_service._resolve_intelligence_mode(
            {"query": "X", "level": "  ExTenDeD "}
        )
        risk_mode, risk_source = web_service._resolve_intelligence_mode(
            {"query": "X", "level": "risk"}
        )

        self.assertEqual((extended_mode, extended_source), ("extended", "level"))
        self.assertEqual((risk_mode, risk_source), ("risk", "level"))

    def test_resolve_intelligence_mode_prefers_canonical_field(self):
        mode, source = web_service._resolve_intelligence_mode(
            {"query": "X", "intelligence_mode": "extended", "level": "risk"}
        )
        self.assertEqual((mode, source), ("extended", "intelligence_mode"))

    def test_resolve_intelligence_mode_rejects_invalid_legacy_level(self):
        with self.assertRaisesRegex(ValueError, "intelligence_mode must be one of"):
            web_service._resolve_intelligence_mode({"query": "X", "level": "future-mode"})


if __name__ == "__main__":
    unittest.main()
