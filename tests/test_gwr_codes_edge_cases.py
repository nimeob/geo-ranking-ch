import importlib.util
import sys
import unittest
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_DIR / "src"
SCRIPT = SRC_DIR / "gwr_codes.py"

spec = importlib.util.spec_from_file_location("gwr_codes", str(SCRIPT))
gwr_codes = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = gwr_codes
spec.loader.exec_module(gwr_codes)


class TestDecodeEdgeCases(unittest.TestCase):
    def test_decode_none_returns_none(self):
        self.assertIsNone(gwr_codes.decode(None, gwr_codes.GSTAT))

    def test_decode_coerces_string_to_int(self):
        self.assertEqual(gwr_codes.decode("1004", gwr_codes.GSTAT), "Bestehend")

    def test_decode_unknown_code_uses_fallback_by_default(self):
        self.assertEqual(gwr_codes.decode(999999, gwr_codes.GSTAT), "Code 999999")

    def test_decode_unknown_code_without_fallback_returns_none(self):
        self.assertIsNone(gwr_codes.decode(999999, gwr_codes.GSTAT, fallback=False))


class TestSummarizeBuildingEdgeCases(unittest.TestCase):
    def test_summarize_building_handles_missing_keys(self):
        out = gwr_codes.summarize_building({})
        self.assertEqual(out["status"], None)
        self.assertEqual(out["kategorie"], None)
        self.assertEqual(out["klasse"], None)
        self.assertIsNone(out["heizung"])
        self.assertIsNone(out["warmwasser"])

    def test_summarize_building_skips_kein_waermeerzeuger(self):
        # 7400/7600 = "Kein Wärmeerzeuger" must be skipped
        attrs = {
            "gwaerzh1": 7400,
            "genh1": 7560,
            "gwaerzw1": 7600,
            "genw1": 7560,
        }
        out = gwr_codes.summarize_building(attrs)
        self.assertIsNone(out["heizung"])
        self.assertIsNone(out["warmwasser"])

    def test_summarize_building_multiple_heaters_and_energy_parens(self):
        attrs = {
            # Heizung 1: Wärmepumpe + Luft
            "gwaerzh1": 7410,
            "genh1": 7501,
            # Heizung 2: Wärmetauscher (inkl. Fernwärme), energy 7500 (=Keine) should omit parens
            "gwaerzh2": 7460,
            "genh2": 7500,

            # Warmwasser 1: Elektroboiler, no energy info
            "gwaerzw1": 7650,
            "genw1": None,
            # Warmwasser 2: Durchlauferhitzer + Elektrizität
            "gwaerzw2": 7636,
            "genw2": 7560,
        }
        out = gwr_codes.summarize_building(attrs)

        self.assertEqual(
            out["heizung"],
            [
                "Wärmepumpe für ein Gebäude (Luft)",
                "Wärmetauscher (inkl. Fernwärme) für ein Gebäude",
            ],
        )
        self.assertEqual(
            out["warmwasser"],
            [
                "Elektroboiler für ein Gebäude",
                "Durchlauferhitzer (Elektrizität)",
            ],
        )


if __name__ == "__main__":
    unittest.main()
