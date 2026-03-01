import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30CheckoutLifecycleContractDocs(unittest.TestCase):
    def test_checkout_lifecycle_doc_exists_with_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "api" / "bl30-checkout-lifecycle-contract-v1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/api/bl30-checkout-lifecycle-contract-v1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-30.2.wp2 — Checkout-/Lifecycle-Contract + idempotenter Entitlement-Sync v1",
            "## Plan-/Produkt-Mapping (Free/Pro/Business)",
            "## Lifecycle-Events (normativ)",
            "## Idempotenz- und Reihenfolgeregeln",
            "## API-Key-Provisioning/Rotation (Folgeregeln)",
            "## Event-/Contract-Auswirkungen auf API/UI",
            "## Guardrails (BL-20 Forward-Compatibility)",
            "## Reproduzierbarer Test-/Doku-Nachweisplan",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Pflichtmarker fehlt: {marker}")

        for must_have in [
            "billing.subscription.created",
            "billing.subscription.upgraded",
            "billing.subscription.downgraded",
            "billing.subscription.canceled",
            "provider:<provider_name>:event_id:<id>",
            "BL30_CHECKOUT_IDEMPOTENCY_REQUIRED",
        ]:
            self.assertIn(must_have, content, msg=f"Pflichtinhalt fehlt im Checkout-Contract: {must_have}")

    def test_backlog_tracks_bl30_2_wp2_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("#466 — BL-30.2.wp2 Checkout-/Lifecycle-Contract + idempotenter Entitlement-Sync (abgeschlossen 2026-03-01)", backlog)
        self.assertIn("[`docs/api/bl30-checkout-lifecycle-contract-v1.md`](api/bl30-checkout-lifecycle-contract-v1.md)", backlog)


if __name__ == "__main__":
    unittest.main()
