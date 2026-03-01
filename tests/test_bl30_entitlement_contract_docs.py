import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30EntitlementContractDocs(unittest.TestCase):
    def test_entitlement_contract_doc_exists_with_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "api" / "bl30-entitlement-contract-v1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/api/bl30-entitlement-contract-v1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-30.2.wp1 — Entitlement-Contract v1 + Gate-Semantik",
            "## Normativer Gate-Katalog v1 (Free/Pro/Business)",
            "## Runtime-Enforcement-Schnittstellen (API/UI)",
            "## Contract-/API-Auswirkungen (additiv, non-breaking)",
            "## Guardrails (BL-20 Forward-Compatibility)",
            "## Reproduzierbarer Nachweispfad (Tests/Doku)",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Pflichtmarker fehlt: {marker}")

        for gate_key in [
            "entitlement.requests.monthly",
            "entitlement.requests.rate_limit",
            "capability.explainability.level",
            "capability.gui.access",
            "capability.trace.debug",
        ]:
            self.assertIn(gate_key, content, msg=f"Gate-Key fehlt im Contract: {gate_key}")

        for guardrail_ref in ["#6", "#127", "BL30_ENTITLEMENT_SCHEMA_ADDITIVE_ONLY"]:
            self.assertIn(guardrail_ref, content, msg=f"Guardrail-Referenz fehlt: {guardrail_ref}")

    def test_backlog_tracks_bl30_2_wp1_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("#465 — BL-30.2.wp1 Entitlement-Contract v1 + Gate-Semantik aus BL-30.1 konsolidieren (abgeschlossen 2026-03-01)", backlog)
        self.assertIn("[`docs/api/bl30-entitlement-contract-v1.md`](api/bl30-entitlement-contract-v1.md)", backlog)


if __name__ == "__main__":
    unittest.main()
