import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ROLLOUT_SCRIPT = REPO_ROOT / "scripts" / "setup_bl31_ui_service_rollout.sh"


class TestBl31UiServiceRolloutScript(unittest.TestCase):
    def test_rollout_script_is_syntax_valid(self):
        cp = subprocess.run(
            ["bash", "-n", str(ROLLOUT_SCRIPT)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)

    def test_rollout_script_contains_required_flow_steps(self):
        text = ROLLOUT_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("ecs update-service", text)
        self.assertIn("aws ecs wait services-stable", text)
        self.assertIn('UI_HEALTH_PATH="${UI_HEALTH_PATH:-/healthz}"', text)
        self.assertIn('API_HEALTH_PATH="${API_HEALTH_PATH:-/health}"', text)

    def test_rollout_script_resolves_target_taskdef_without_max_items_none_artifact(self):
        text = ROLLOUT_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("--query 'taskDefinitionArns'", text)
        self.assertIn("grep -v '^None$'", text)
        self.assertNotIn("--max-items 1", text)
        self.assertNotIn("taskDefinitionArns[0]", text)


if __name__ == "__main__":
    unittest.main()
