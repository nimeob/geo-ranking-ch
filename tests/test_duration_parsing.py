import unittest

from src.api.duration_parsing import parse_duration_seconds


class TestParseDurationSeconds(unittest.TestCase):
    def test_parses_plain_seconds(self):
        self.assertEqual(parse_duration_seconds("60", field_name="x"), 60.0)
        self.assertEqual(parse_duration_seconds(60, field_name="x"), 60.0)
        self.assertEqual(parse_duration_seconds("1e3", field_name="x"), 1000.0)

    def test_parses_unit_suffixes(self):
        self.assertEqual(parse_duration_seconds("30s", field_name="x"), 30.0)
        self.assertEqual(parse_duration_seconds("15m", field_name="x"), 15.0 * 60.0)
        self.assertEqual(parse_duration_seconds("24h", field_name="x"), 24.0 * 3600.0)
        self.assertEqual(parse_duration_seconds("7d", field_name="x"), 7.0 * 86400.0)
        self.assertEqual(parse_duration_seconds(" 1.5H ", field_name="x"), 1.5 * 3600.0)

    def test_rejects_invalid(self):
        for raw in ("", "-1", "-1h", "abc", "7w", "nan", "inf"):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    parse_duration_seconds(raw, field_name="x")


if __name__ == "__main__":
    unittest.main()
