import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestWebhookGateHostingerRunbookDocs(unittest.TestCase):
    def test_runbook_contains_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "WEBHOOK_GATE_HOSTINGER_RUNBOOK.md"
        self.assertTrue(doc_path.is_file(), msg="docs/WEBHOOK_GATE_HOSTINGER_RUNBOOK.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-16.wp1 — AWS-Webhook-Gate Runbook (Hostinger) · Issue #549",
            "infra/webhook_gate/nginx.aws-alarm.conf.template",
            "infra/webhook_gate/docker-compose.webhook-gate.template.yml",
            "scripts/check_webhook_gate_templates.py",
            "python3 scripts/check_webhook_gate_templates.py --repo-root . --render-example",
            "#550",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt im Runbook: {marker}")

    def test_operations_references_runbook(self):
        operations = (REPO_ROOT / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")
        self.assertIn("WEBHOOK_GATE_HOSTINGER_RUNBOOK.md", operations)


if __name__ == "__main__":
    unittest.main()
