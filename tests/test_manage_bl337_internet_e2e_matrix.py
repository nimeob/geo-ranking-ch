from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "manage_bl337_internet_e2e_matrix.py"

spec = importlib.util.spec_from_file_location("manage_bl337_internet_e2e_matrix", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class TestManageBl337InternetE2EMatrix(unittest.TestCase):
    def test_generate_and_validate_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "matrix.json"

            rc_generate = module.main(
                [
                    "--output",
                    str(out),
                    "--generated-at-utc",
                    "2026-03-01T00:00:00Z",
                ]
            )
            self.assertEqual(rc_generate, 0)
            self.assertTrue(out.exists())

            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["schemaVersion"], "bl337.internet-e2e.v1")
            self.assertEqual(payload["summary"]["total"], len(payload["tests"]))
            self.assertGreaterEqual(len(payload["tests"]), 8)

            required_case_keys = {
                "testId",
                "area",
                "title",
                "preconditions",
                "steps",
                "expectedResult",
                "actualResult",
                "status",
                "evidenceLinks",
                "notes",
            }
            for case in payload["tests"]:
                self.assertTrue(required_case_keys.issubset(case.keys()))

            rc_validate = module.main(["--validate", str(out)])
            self.assertEqual(rc_validate, 0)

    def test_validate_fails_for_missing_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "matrix-invalid.json"
            payload = module.build_matrix(
                api_base_url="https://api.dev.georanking.ch",
                app_base_url="https://www.dev.georanking.ch",
                generated_at_utc="2026-03-01T00:00:00Z",
            )
            payload["tests"][0].pop("expectedResult")
            out.write_text(json.dumps(payload), encoding="utf-8")

            rc_validate = module.main(["--validate", str(out)])
            self.assertEqual(rc_validate, 1)

    def test_require_actual_mode_rejects_unexecuted_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "matrix.json"
            module.main(["--output", str(out), "--generated-at-utc", "2026-03-01T00:00:00Z"])

            rc_validate = module.main(["--validate", str(out), "--require-actual"])
            self.assertEqual(rc_validate, 1)


if __name__ == "__main__":
    unittest.main()
