from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_bl31_service_boundaries.py"


class TestCheckBl31ServiceBoundaries(unittest.TestCase):
    def test_current_repo_src_passes_boundary_guard(self) -> None:
        result = subprocess.run(
            [str(SCRIPT), "--src-dir", str(REPO_ROOT / "src")],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("passed", result.stdout.lower())

    def test_ui_importing_api_module_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src_dir = Path(tmp) / "src"
            src_dir.mkdir(parents=True, exist_ok=True)

            (src_dir / "web_service.py").write_text("", encoding="utf-8")
            (src_dir / "address_intel.py").write_text("", encoding="utf-8")
            (src_dir / "personalized_scoring.py").write_text("", encoding="utf-8")
            (src_dir / "suitability_light.py").write_text("", encoding="utf-8")
            (src_dir / "ui_service.py").write_text("import src.address_intel\n", encoding="utf-8")
            (src_dir / "gui_mvp.py").write_text("", encoding="utf-8")
            (src_dir / "geo_utils.py").write_text("", encoding="utf-8")
            (src_dir / "gwr_codes.py").write_text("", encoding="utf-8")
            (src_dir / "mapping_transform_rules.py").write_text("", encoding="utf-8")

            result = subprocess.run(
                [str(SCRIPT), "--src-dir", str(src_dir)],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("must not import API module", result.stdout)

    def test_shared_module_must_remain_neutral(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src_dir = Path(tmp) / "src"
            src_dir.mkdir(parents=True, exist_ok=True)

            (src_dir / "web_service.py").write_text("", encoding="utf-8")
            (src_dir / "address_intel.py").write_text("", encoding="utf-8")
            (src_dir / "personalized_scoring.py").write_text("", encoding="utf-8")
            (src_dir / "suitability_light.py").write_text("", encoding="utf-8")
            (src_dir / "ui_service.py").write_text("", encoding="utf-8")
            (src_dir / "gui_mvp.py").write_text("from src.web_service import app\n", encoding="utf-8")
            (src_dir / "geo_utils.py").write_text("", encoding="utf-8")
            (src_dir / "gwr_codes.py").write_text("", encoding="utf-8")
            (src_dir / "mapping_transform_rules.py").write_text("", encoding="utf-8")

            result = subprocess.run(
                [str(SCRIPT), "--src-dir", str(src_dir)],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("must remain neutral", result.stdout)

    def test_split_layout_passes_with_shared_only_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src_dir = Path(tmp) / "src"
            (src_dir / "api").mkdir(parents=True, exist_ok=True)
            (src_dir / "ui").mkdir(parents=True, exist_ok=True)
            (src_dir / "shared").mkdir(parents=True, exist_ok=True)

            (src_dir / "api" / "analyze.py").write_text("from src.shared.helpers import helper\n", encoding="utf-8")
            (src_dir / "ui" / "app.py").write_text("from src.shared.helpers import helper\n", encoding="utf-8")
            (src_dir / "shared" / "helpers.py").write_text("def helper():\n    return 1\n", encoding="utf-8")

            result = subprocess.run(
                [str(SCRIPT), "--src-dir", str(src_dir)],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("mode: split", result.stdout)

    def test_split_layout_rejects_ui_importing_api(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src_dir = Path(tmp) / "src"
            (src_dir / "api").mkdir(parents=True, exist_ok=True)
            (src_dir / "ui").mkdir(parents=True, exist_ok=True)
            (src_dir / "shared").mkdir(parents=True, exist_ok=True)

            (src_dir / "api" / "analyze.py").write_text("", encoding="utf-8")
            (src_dir / "ui" / "app.py").write_text("from src.api.analyze import run\n", encoding="utf-8")
            (src_dir / "shared" / "helpers.py").write_text("", encoding="utf-8")

            result = subprocess.run(
                [str(SCRIPT), "--src-dir", str(src_dir)],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("must not import API module", result.stdout)


if __name__ == "__main__":
    unittest.main()
