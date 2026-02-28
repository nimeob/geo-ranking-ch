import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TASKDEF_TEMPLATE = REPO_ROOT / "infra" / "ecs" / "taskdef.swisstopo-dev-ui.json"


class TestBl31UiTaskDefinitionRoles(unittest.TestCase):
    def test_ui_taskdef_uses_project_specific_roles(self):
        payload = json.loads(TASKDEF_TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual(
            payload.get("executionRoleArn"),
            "arn:aws:iam::523234426229:role/swisstopo-dev-ecs-execution-role",
        )
        self.assertEqual(
            payload.get("taskRoleArn"),
            "arn:aws:iam::523234426229:role/swisstopo-dev-ecs-task-role",
        )


if __name__ == "__main__":
    unittest.main()
