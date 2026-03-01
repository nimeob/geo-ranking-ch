import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30ParentDependencyGatesPhasePlanDocs(unittest.TestCase):
    def test_doc_exists_with_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "BL30_PARENT_DEPENDENCY_GATES_PHASE_PLAN_V1.md"
        self.assertTrue(doc_path.is_file(), msg="docs/BL30_PARENT_DEPENDENCY_GATES_PHASE_PLAN_V1.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        required_markers = [
            "# BL-30.parent.wp1 — Dependency-Gates + Reihenfolgeplan v1 (Issue #509)",
            "## Gate-Matrix (GO / HOLD / BLOCKED)",
            "## Entscheidungslogik",
            "## Reihenfolge-/Phasenplan (BL-30.2)",
            "### Phase 1 — Leaf #465 (oldest-first)",
            "### Phase 2 — Leaf #466",
            "## Operative Regel",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in BL-30 Parent Gate-/Phasen-Doku: {marker}")

        for required_term in ["#6", "#127", "#457", "BLOCKED", "#465 -> #466"]:
            self.assertIn(required_term, content, msg=f"Pflichtbegriff fehlt in BL-30 Parent Gate-/Phasen-Doku: {required_term}")

    def test_backlog_references_wp1_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn(
            "#509 — BL-30.parent.wp1 Dependency-Gates + Reihenfolgeplan v1 für BL-30.2 dokumentieren (abgeschlossen 2026-03-01)",
            backlog,
        )
        self.assertIn("[`docs/BL30_PARENT_DEPENDENCY_GATES_PHASE_PLAN_V1.md`](BL30_PARENT_DEPENDENCY_GATES_PHASE_PLAN_V1.md)", backlog)


if __name__ == "__main__":
    unittest.main()
