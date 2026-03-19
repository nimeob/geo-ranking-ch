import importlib
import unittest


class TestLegacyWrapperConsistency(unittest.TestCase):
    def test_alias_wrappers_resolve_to_canonical_modules(self):
        cases = [
            ("src.web_service", "src.api.web_service"),
            ("src.personalized_scoring", "src.api.personalized_scoring"),
            ("src.suitability_light", "src.api.suitability_light"),
            ("src.ui_service", "src.ui.service"),
            ("src.gui_mvp", "src.shared.gui_mvp"),
        ]

        for legacy_name, canonical_name in cases:
            with self.subTest(legacy=legacy_name):
                legacy_module = importlib.import_module(legacy_name)
                canonical_module = importlib.import_module(canonical_name)
                self.assertIs(legacy_module, canonical_module)

    def test_address_intel_wrapper_forwards_attribute_mutations(self):
        legacy_module = importlib.import_module("src.address_intel")
        canonical_module = importlib.import_module("src.api.address_intel")

        sentinel_name = "_wrapper_forwarding_test_value"
        setattr(legacy_module, sentinel_name, 123)
        try:
            self.assertEqual(getattr(canonical_module, sentinel_name), 123)
            self.assertEqual(getattr(legacy_module, sentinel_name), 123)
            delattr(legacy_module, sentinel_name)
            self.assertFalse(hasattr(canonical_module, sentinel_name))
        finally:
            if hasattr(legacy_module, sentinel_name):
                delattr(legacy_module, sentinel_name)
            if hasattr(canonical_module, sentinel_name):
                delattr(canonical_module, sentinel_name)


if __name__ == "__main__":
    unittest.main()
