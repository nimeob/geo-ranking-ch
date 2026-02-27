import unittest
from unittest import mock

from src.web_service import _resolve_port


class TestResolvePort(unittest.TestCase):
    def test_prefers_port_when_set(self):
        with mock.patch.dict("os.environ", {"PORT": "9090", "WEB_PORT": "8081"}, clear=False):
            self.assertEqual(_resolve_port(), 9090)

    def test_falls_back_to_web_port_when_port_missing_or_blank(self):
        with mock.patch.dict("os.environ", {"WEB_PORT": "8181"}, clear=True):
            self.assertEqual(_resolve_port(), 8181)

        with mock.patch.dict("os.environ", {"PORT": "   ", "WEB_PORT": "8282"}, clear=True):
            self.assertEqual(_resolve_port(), 8282)

    def test_raises_value_error_for_invalid_port_inputs(self):
        with mock.patch.dict("os.environ", {"PORT": "abc"}, clear=True):
            with self.assertRaises(ValueError):
                _resolve_port()

        with mock.patch.dict("os.environ", {"PORT": "", "WEB_PORT": "-"}, clear=True):
            with self.assertRaises(ValueError):
                _resolve_port()


if __name__ == "__main__":
    unittest.main()
