import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30DeepModeOrchestrationDocs(unittest.TestCase):
    def test_orchestration_doc_exists_with_required_sections(self):
        doc_path = REPO_ROOT / "docs" / "api" / "deep-mode-orchestration-guardrails-v1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/api/deep-mode-orchestration-guardrails-v1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-30.3.wp2 — Deep-Mode-Orchestrierung + Runtime-Guardrails (Design v1)",
            "## Ausführungssequenz (v1)",
            "## Laufzeit-/Kosten-Guardrails (v1)",
            "## Trennung Baseline vs. Deep-Enrichment",
            "## Telemetrie-/Tracing-Anforderungen (Mindeststandard)",
            "## Risiken / offene Punkte",
            "## Follow-up-Issues",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in Deep-Mode-Orchestrierungsdoku: {marker}")

        required_terms = [
            "options.capabilities.deep_mode.requested",
            "result.status.capabilities.deep_mode",
            "api.deep_mode.execution.start",
            "fallback_reason",
            "#470",
            "#472",
            "#473",
        ]
        for term in required_terms:
            self.assertIn(term, content, msg=f"Pflichtbegriff fehlt in Deep-Mode-Orchestrierungsdoku: {term}")

    def test_contract_v1_references_orchestration_doc(self):
        contract_doc = (REPO_ROOT / "docs" / "api" / "contract-v1.md").read_text(encoding="utf-8")
        self.assertIn(
            "[`docs/api/deep-mode-orchestration-guardrails-v1.md`](./deep-mode-orchestration-guardrails-v1.md)",
            contract_doc,
            msg="contract-v1 muss auf die Deep-Mode-Orchestrierungsdoku verlinken",
        )

    def test_backlog_tracks_bl30_wp2_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn(
            "#469 — BL-30.3.wp2 Deep-Mode-Orchestrierung + Runtime-Guardrails designen (abgeschlossen 2026-03-01)",
            backlog,
        )
        self.assertIn("tests/test_bl30_deep_mode_orchestration_docs.py", backlog)


if __name__ == "__main__":
    unittest.main()
