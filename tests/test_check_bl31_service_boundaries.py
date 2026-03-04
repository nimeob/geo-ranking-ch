from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_bl31_service_boundaries.py"

# Maintenance note:
# Keep this suite aligned with scripts/check_bl31_service_boundaries.py policy sets.
# If API/UI/shared module constants or route ownership rules change, update the
# fixture builders and expected violation strings here in the same PR.
_SPEC = importlib.util.spec_from_file_location("check_bl31_service_boundaries", SCRIPT)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load boundary check script module from {SCRIPT}")
_boundary_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_boundary_module)

LEGACY_POLICY_MODULES = {
    "web_service.py": "",
    "address_intel.py": "",
    "personalized_scoring.py": "",
    "suitability_light.py": "",
    "ui_service.py": "",
    "gui_mvp.py": "",
    "geo_utils.py": "",
    "gwr_codes.py": "",
    "mapping_transform_rules.py": "",
}


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

    def _build_legacy_src(self, root: Path, overrides: dict[str, str] | None = None) -> Path:
        src_dir = root / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        contents = dict(LEGACY_POLICY_MODULES)
        if overrides:
            contents.update(overrides)
        for module_name, text in contents.items():
            (src_dir / module_name).write_text(text, encoding="utf-8")
        return src_dir

    def _analyze(self, src_dir: Path) -> list[str]:
        violations = _boundary_module.analyze_service_boundaries(src_dir)
        self.assertIsInstance(violations, list)
        return violations

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

    def test_legacy_import_boundary_matrix_allows_expected_paths(self) -> None:
        positive_cases = [
            (
                "api may import shared",
                {"web_service.py": "from src.geo_utils import helper\n"},
            ),
            (
                "ui may import shared",
                {"ui_service.py": "from src.mapping_transform_rules import RULES\n"},
            ),
            (
                "shared may import shared",
                {"geo_utils.py": "from src.gwr_codes import CODE\n"},
            ),
        ]

        for case_name, overrides in positive_cases:
            with self.subTest(case=case_name):
                with tempfile.TemporaryDirectory() as tmp:
                    src_dir = self._build_legacy_src(Path(tmp), overrides)
                    violations = self._analyze(src_dir)
                    self.assertEqual([], violations)

    def test_legacy_import_boundary_matrix_rejects_forbidden_paths_with_clear_messages(self) -> None:
        negative_cases = [
            (
                "api importing ui",
                {"web_service.py": "from src.ui_service import app\n"},
                "API module 'web_service' must not import UI module 'ui_service'",
            ),
            (
                "ui importing api",
                {"ui_service.py": "from src.address_intel import score\n"},
                "UI module 'ui_service' must not import API module 'address_intel'",
            ),
            (
                "shared importing api",
                {"geo_utils.py": "from src.personalized_scoring import rank\n"},
                "Shared module 'geo_utils' must remain neutral and not import API module 'personalized_scoring'",
            ),
        ]

        for case_name, overrides, expected_message in negative_cases:
            with self.subTest(case=case_name):
                with tempfile.TemporaryDirectory() as tmp:
                    src_dir = self._build_legacy_src(Path(tmp), overrides)
                    violations = self._analyze(src_dir)
                    self.assertIn(expected_message, violations)

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

    def test_split_layout_rejects_api_route_outside_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src_dir = Path(tmp) / "src"
            (src_dir / "api").mkdir(parents=True, exist_ok=True)
            (src_dir / "ui").mkdir(parents=True, exist_ok=True)
            (src_dir / "shared").mkdir(parents=True, exist_ok=True)

            (src_dir / "api" / "web_service.py").write_text(
                """
from http.server import BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        request_path = \"/internal/ui-only\"
        if request_path == \"/internal/ui-only\":
            return
""".strip(),
                encoding="utf-8",
            )
            (src_dir / "ui" / "service.py").write_text("", encoding="utf-8")
            (src_dir / "shared" / "helpers.py").write_text("", encoding="utf-8")

            result = subprocess.run(
                [str(SCRIPT), "--src-dir", str(src_dir)],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("API route policy violation", result.stdout)

    def test_split_layout_rejects_ui_route_claiming_api_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src_dir = Path(tmp) / "src"
            (src_dir / "api").mkdir(parents=True, exist_ok=True)
            (src_dir / "ui").mkdir(parents=True, exist_ok=True)
            (src_dir / "shared").mkdir(parents=True, exist_ok=True)

            (src_dir / "api" / "web_service.py").write_text("", encoding="utf-8")
            (src_dir / "ui" / "service.py").write_text(
                """
from http.server import BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        request_path = \"/api/v1/diagnostics\"
        if request_path.startswith(\"/api/\"):
            return
""".strip(),
                encoding="utf-8",
            )
            (src_dir / "shared" / "helpers.py").write_text("", encoding="utf-8")

            result = subprocess.run(
                [str(SCRIPT), "--src-dir", str(src_dir)],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("UI route policy violation", result.stdout)


if __name__ == "__main__":
    unittest.main()
