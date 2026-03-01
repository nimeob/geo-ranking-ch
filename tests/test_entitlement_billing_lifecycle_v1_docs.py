import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestEntitlementBillingLifecycleV1Docs(unittest.TestCase):
    def test_doc_contains_required_sections_and_markers(self):
        doc_path = REPO_ROOT / "docs" / "api" / "entitlement-billing-lifecycle-v1.md"
        self.assertTrue(
            doc_path.is_file(),
            msg="docs/api/entitlement-billing-lifecycle-v1.md fehlt",
        )

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# Entitlement-/Billing-Lifecycle v1 (GTM Follow-up)",
            "Issue: #586 (Parent #577)",
            "## 1) Capability-/Entitlement-Modell v1",
            "## 2) Billing-/Subscription-Zustände und Übergangsregeln",
            "## 3) Idempotente Webhook-Strategie + Fehlerbehandlung",
            "## 4) Usage-/Metering-Modell (Org/User/API-Key)",
            "## 5) Non-Goals / offene Risiken",
            "## DoD-Abdeckung (#586)",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Pflichtmarker fehlt: {marker}")

        required_tokens = [
            "entitlement.requests.monthly",
            "billing.payment.failed",
            "provider:<provider_name>:event_id:<event_id>",
            "scope_type",
            "scope_id",
            "suspended",
            "grace",
            "past_due",
        ]
        for token in required_tokens:
            self.assertIn(token, content, msg=f"Pflichttoken fehlt: {token}")

    def test_backlog_tracks_issue_586_completion_and_next_step(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("#586 abgeschlossen", backlog)
        self.assertIn(
            "[`docs/api/entitlement-billing-lifecycle-v1.md`](api/entitlement-billing-lifecycle-v1.md)",
            backlog,
        )
        self.assertIn("BL-30-Follow-up #588", backlog)


if __name__ == "__main__":
    unittest.main()
