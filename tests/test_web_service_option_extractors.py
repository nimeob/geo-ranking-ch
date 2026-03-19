import importlib
import unittest


web_service = importlib.import_module("src.api.web_service")


class TestWebServiceOptionExtractors(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
