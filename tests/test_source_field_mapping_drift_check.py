import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DRIFT_CHECK = REPO_ROOT / "scripts" / "check_source_field_mapping_drift.py"
VALID_SAMPLES = REPO_ROOT / "tests" / "data" / "mapping" / "source_schema_samples.ch.v1.json"
MISSING_LON_SAMPLES = (
    REPO_ROOT / "tests" / "data" / "mapping" / "source_schema_samples.missing_lon.json"
)


class TestSourceFieldMappingDriftCheck(unittest.TestCase):
    def test_drift_check_passes_for_reference_samples(self):
        proc = subprocess.run(
            [sys.executable, str(DRIFT_CHECK), "--samples", str(VALID_SAMPLES)],
            cwd=str(REPO_ROOT),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=(
                "drift check sollte mit Referenz-Samples erfolgreich sein:\n"
                f"stdout:\n{proc.stdout}\n"
                f"stderr:\n{proc.stderr}"
            ),
        )
        self.assertIn("source-field-mapping drift check OK", proc.stdout)

    def test_drift_check_fails_with_clear_error_on_missing_field(self):
        proc = subprocess.run(
            [sys.executable, str(DRIFT_CHECK), "--samples", str(MISSING_LON_SAMPLES)],
            cwd=str(REPO_ROOT),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0, msg="drift check muss bei fehlendem Feld fehlschlagen")
        self.assertIn("source-field-mapping drift check FAILED", proc.stdout)
        self.assertIn("source=geoadmin_search", proc.stdout)
        self.assertIn("results[].attrs.lon", proc.stdout)


if __name__ == "__main__":
    unittest.main()
