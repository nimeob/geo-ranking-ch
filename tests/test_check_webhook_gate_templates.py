import importlib.util
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_webhook_gate_templates.py"
NGINX_TEMPLATE_PATH = REPO_ROOT / "infra" / "webhook_gate" / "nginx.aws-alarm.conf.template"
COMPOSE_TEMPLATE_PATH = REPO_ROOT / "infra" / "webhook_gate" / "docker-compose.webhook-gate.template.yml"


spec = importlib.util.spec_from_file_location("check_webhook_gate_templates", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
spec.loader.exec_module(module)


class TestCheckWebhookGateTemplates(unittest.TestCase):
    def test_cli_passes_for_repo_templates(self):
        result = subprocess.run(
            ["python3", str(SCRIPT_PATH), "--repo-root", str(REPO_ROOT), "--render-example"],
            cwd=str(REPO_ROOT),
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("webhook gate template check: PASS", result.stdout)

    def test_validation_reports_missing_placeholder(self):
        nginx = NGINX_TEMPLATE_PATH.read_text(encoding="utf-8")
        compose = COMPOSE_TEMPLATE_PATH.read_text(encoding="utf-8")
        mutated = nginx.replace("__ALARM_TOKEN__", "fixed-token", 1)

        errors = module.validate_templates_from_text(mutated, compose)

        self.assertTrue(errors)
        self.assertTrue(any("__ALARM_TOKEN__" in err for err in errors))


if __name__ == "__main__":
    unittest.main()
