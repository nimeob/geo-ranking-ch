import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestMVPToScaleRolloutPlanV1Docs(unittest.TestCase):
    def test_doc_contains_required_sections_and_followup_issue_links(self):
        doc_path = REPO_ROOT / "docs" / "MVP_TO_SCALE_ROLLOUT_PLAN_V1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/MVP_TO_SCALE_ROLLOUT_PLAN_V1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# MVP→Scale Rollout-Plan v1 (GTM Follow-up)",
            "Issue: #588 (Parent #577)",
            "## 1) Leitplanken (verbindlich)",
            "## 2) Stufenplan MVP→Scale",
            "## 3) Risiken + Mitigations pro Stufe",
            "## 4) No-regrets Defaults + Trade-offs",
            "## 5) Atomisierte Folge-Issues (0.5–2 Tage)",
            "## 6) Abnahmekriterien für Abschluss von #577",
            "## DoD-Abdeckung (#588)",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Pflichtmarker fehlt: {marker}")

        required_tokens = [
            "#592",
            "#593",
            "#594",
            "#592 -> #593 -> #594",
            "Keine Breaking Contracts",
            "Cleanup-Jobs mit Dry-run-Modus",
            "oldest-first",
        ]
        for token in required_tokens:
            self.assertIn(token, content, msg=f"Pflichttoken fehlt: {token}")

    def test_backlog_tracks_issue_588_completion_and_followup_chain(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("#588 abgeschlossen", backlog)
        self.assertIn(
            "[`docs/MVP_TO_SCALE_ROLLOUT_PLAN_V1.md`](MVP_TO_SCALE_ROLLOUT_PLAN_V1.md)",
            backlog,
        )
        self.assertIn("#592/#593/#594", backlog)


if __name__ == "__main__":
    unittest.main()
