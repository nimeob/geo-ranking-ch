import json
import unittest
from pathlib import Path

from src.mapping_transform_rules import (
    EXTERNAL_RULES,
    TRANSFORM_RULE_HANDLERS,
    normalize_observed_at_iso,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = REPO_ROOT / "tests" / "data" / "mapping" / "transform_rules_golden.json"


class TestMappingTransformRulesGolden(unittest.TestCase):
    def test_golden_cases(self):
        payload = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
        cases = payload.get("cases", [])
        self.assertTrue(cases, msg="Keine Golden-Cases definiert")

        for case in cases:
            name = case.get("name", "unnamed")
            rule = case["rule"]
            handler = TRANSFORM_RULE_HANDLERS.get(rule)
            self.assertIsNotNone(handler, msg=f"Unbekannte Rule im Golden-Set: {rule}")

            with self.subTest(name=name, rule=rule):
                kwargs = case.get("kwargs") or {}
                actual = handler(case.get("input"), **kwargs)
                self.assertEqual(actual, case.get("expected"), msg=f"Golden-Drift in {name}")

    def test_tr04_is_explicitly_marked_as_external(self):
        self.assertIn("TR-04", EXTERNAL_RULES)
        self.assertIn("gwr_codes", EXTERNAL_RULES["TR-04"])

    def test_epoch_timestamp_supported_for_tr08(self):
        iso = normalize_observed_at_iso(0)
        self.assertEqual(iso, "1970-01-01T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
