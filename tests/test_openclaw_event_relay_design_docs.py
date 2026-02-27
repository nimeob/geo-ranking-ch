import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestOpenClawEventRelayDesignDocs(unittest.TestCase):
    def test_event_relay_design_doc_exists_with_required_sections(self):
        doc_path = REPO_ROOT / "docs" / "automation" / "openclaw-event-relay-design.md"
        self.assertTrue(doc_path.is_file(), msg="docs/automation/openclaw-event-relay-design.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-20.y.wp2.r1 — Event-Relay-Design für Issue/PR-nahe OpenClaw-Automation",
            "kein inbound Webhook-Target",
            "## Ziel-Events und Reaktionszeit",
            "X-Hub-Signature-256",
            "## Migrations- und Fallback-Plan",
            "reports/automation/event-relay/",
            "#233",
        ]

        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in openclaw-event-relay-design.md: {marker}")

    def test_mapping_and_operations_reference_event_relay_design(self):
        mapping_path = REPO_ROOT / "docs" / "automation" / "openclaw-job-mapping.md"
        ops_path = REPO_ROOT / "docs" / "OPERATIONS.md"

        mapping_content = mapping_path.read_text(encoding="utf-8")
        ops_content = ops_path.read_text(encoding="utf-8")

        self.assertIn(
            "openclaw-event-relay-design.md",
            mapping_content,
            msg="openclaw-job-mapping.md referenziert das Event-Relay-Design nicht",
        )
        self.assertIn("#227", mapping_content)
        self.assertIn("#233", mapping_content)

        self.assertIn(
            "openclaw-event-relay-design.md",
            ops_content,
            msg="OPERATIONS.md referenziert das Event-Relay-Design nicht",
        )
        self.assertIn("#233", ops_content)


if __name__ == "__main__":
    unittest.main()
