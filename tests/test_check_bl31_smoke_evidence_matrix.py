from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_bl31_smoke_evidence_matrix.py"

spec = importlib.util.spec_from_file_location("check_bl31_smoke_evidence_matrix", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class TestCheckBl31SmokeEvidenceMatrix(unittest.TestCase):
    def _write_artifact(self, path: Path, mode: str) -> None:
        payload = {
            "timestampUtc": "20260228T170000Z",
            "mode": mode,
            "execute": False,
            "result": "planned",
            "region": "eu-central-1",
            "cluster": "swisstopo-dev",
            "taskDefinitionBefore": {
                "api": "not-collected (dry-run)",
                "ui": "not-collected (dry-run)",
            },
            "taskDefinitionAfter": {
                "api": "not-collected (dry-run)",
                "ui": "not-collected (dry-run)",
            },
            "smokeArtifacts": [],
            "steps": [],
        }
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_main_passes_for_all_required_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            api = tmp_path / "20260228T170000Z-bl31-split-deploy-api.json"
            ui = tmp_path / "20260228T170100Z-bl31-split-deploy-ui.json"
            both = tmp_path / "20260228T170200Z-bl31-split-deploy-both.json"

            self._write_artifact(api, "api")
            self._write_artifact(ui, "ui")
            self._write_artifact(both, "both")

            rc = module.main([str(api), str(ui), str(both)])
            self.assertEqual(rc, 0)

    def test_main_fails_when_required_mode_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            api = tmp_path / "20260228T170000Z-bl31-split-deploy-api.json"
            self._write_artifact(api, "api")

            rc = module.main([str(api), "--require-modes", "api,ui"])
            self.assertEqual(rc, 1)

    def test_default_scan_ignores_schemafremde_smoke_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts_dir = Path(tmp) / "artifacts" / "bl31"
            artifacts_dir.mkdir(parents=True, exist_ok=True)

            self._write_artifact(artifacts_dir / "20260228T170000Z-bl31-split-deploy-api.json", "api")
            self._write_artifact(artifacts_dir / "20260228T170100Z-bl31-split-deploy-ui.json", "ui")
            self._write_artifact(artifacts_dir / "20260228T170200Z-bl31-split-deploy-both.json", "both")

            # Dieses Artefakt gehört zu einem anderen Schema und darf den Default-Scan nicht kippen.
            (artifacts_dir / "20260228T170300Z-bl31-split-deploy-ui-smoke.json").write_text(
                json.dumps({"status": "ok", "kind": "ui-smoke"}),
                encoding="utf-8",
            )

            old_cwd = Path.cwd()
            try:
                os.chdir(tmp)
                rc = module.main([])
            finally:
                os.chdir(old_cwd)

            self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
