from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_bl31_split_deploy.py"

spec = importlib.util.spec_from_file_location("run_bl31_split_deploy", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class TestRunBl31SplitDeploy(unittest.TestCase):
    def test_resolve_steps_dispatches_mode_correctly(self) -> None:
        self.assertEqual(module.resolve_steps("api"), ["api"])
        self.assertEqual(module.resolve_steps("ui"), ["ui"])
        self.assertEqual(module.resolve_steps("both"), ["api", "ui"])

    def test_guardrail_detects_cross_service_drift(self) -> None:
        with self.assertRaises(RuntimeError) as api_only_err:
            module._assert_service_local_guardrail(
                selected_key="api",
                before_api_taskdef="api:1",
                before_ui_taskdef="ui:1",
                after_api_taskdef="api:2",
                after_ui_taskdef="ui:2",
            )
        self.assertIn("API-only step changed UI", str(api_only_err.exception))

        with self.assertRaises(RuntimeError) as ui_only_err:
            module._assert_service_local_guardrail(
                selected_key="ui",
                before_api_taskdef="api:3",
                before_ui_taskdef="ui:3",
                after_api_taskdef="api:4",
                after_ui_taskdef="ui:4",
            )
        self.assertIn("UI-only step changed API", str(ui_only_err.exception))

    def test_dry_run_plan_contains_ordered_steps_and_guardrails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "artifacts"
            config = module.Config(
                mode="both",
                execute=False,
                aws_region="eu-central-1",
                ecs_cluster="swisstopo-dev",
                api_service="swisstopo-dev-api",
                ui_service="swisstopo-dev-ui",
                smoke_script="./scripts/run_bl31_routing_tls_smoke.sh",
                out_dir=out_dir,
            )

            payload = module.execute_deploy(config)
            self.assertEqual(payload["mode"], "both")
            self.assertFalse(payload["execute"])

            plan = payload["plan"]
            self.assertEqual([step["step"] for step in plan], ["api", "ui"])
            self.assertIn("swisstopo-dev-ui task definition must remain unchanged", plan[0]["guardrail"])
            self.assertIn("swisstopo-dev-api task definition must remain unchanged", plan[1]["guardrail"])

    def test_main_writes_dry_run_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_json = Path(tmp) / "split-deploy.json"
            rc = module.main(
                [
                    "--mode",
                    "api",
                    "--out-dir",
                    str(Path(tmp) / "artifacts"),
                    "--output-json",
                    str(output_json),
                ]
            )
            self.assertEqual(rc, 0)
            payload = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["mode"], "api")
            self.assertFalse(payload["execute"])
            self.assertEqual(payload["plan"][0]["step"], "api")


if __name__ == "__main__":
    unittest.main()
