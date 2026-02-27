import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

CORE_MODULES = [
    "src/web_service.py",
    "src/address_intel.py",
    "src/personalized_scoring.py",
    "src/suitability_light.py",
    "src/legacy_consumer_fingerprint.py",
]


class TestCoreModuleDocstrings(unittest.TestCase):
    def test_core_modules_expose_module_docstrings(self):
        for relative_path in CORE_MODULES:
            module_path = REPO_ROOT / relative_path
            self.assertTrue(module_path.is_file(), msg=f"Modul fehlt: {relative_path}")

            source = module_path.read_text(encoding="utf-8")
            module = ast.parse(source)
            docstring = ast.get_docstring(module)

            with self.subTest(module=relative_path):
                self.assertIsNotNone(docstring, msg=f"Modul-Docstring fehlt: {relative_path}")
                self.assertGreaterEqual(
                    len(docstring.strip()),
                    20,
                    msg=f"Modul-Docstring zu knapp: {relative_path}",
                )


if __name__ == "__main__":
    unittest.main()
