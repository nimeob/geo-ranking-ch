import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30DeepModeRuntimeOrchestratorDocs(unittest.TestCase):
    def test_orchestration_doc_mentions_runtime_implementation_status(self):
        doc_path = REPO_ROOT / "docs" / "api" / "deep-mode-orchestration-guardrails-v1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/api/deep-mode-orchestration-guardrails-v1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "### Implementierungsstand (#472)",
            "result.status.capabilities.deep_mode",
            "result.status.entitlements.deep_mode",
            "requested` → `profile/policy` → `allowed` → `quota_remaining` → Zeitbudget",
            "#472 — ✅ BL-30.3.wp2.r1 Runtime-Orchestrator-Implementierung",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in Runtime-Orchestrator-Doku: {marker}")

    def test_backlog_tracks_bl30_wp2_r1_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn(
            "#472 — BL-30.3.wp2.r1 Runtime-Orchestrator im `/analyze`-Flow implementieren (abgeschlossen 2026-03-01)",
            backlog,
        )
        self.assertIn("tests/test_bl30_deep_mode_runtime_orchestrator.py", backlog)


if __name__ == "__main__":
    unittest.main()
