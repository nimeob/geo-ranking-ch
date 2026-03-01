import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBL30ParentRebuildVsAusbauGuardrailsDocs(unittest.TestCase):
    def test_doc_exists_with_required_markers(self):
        doc_path = REPO_ROOT / "docs" / "BL30_REBUILD_VS_AUSBAU_GUARDRAILS_API_FIRST_V1.md"
        self.assertTrue(
            doc_path.is_file(),
            msg="docs/BL30_REBUILD_VS_AUSBAU_GUARDRAILS_API_FIRST_V1.md fehlt",
        )

        content = doc_path.read_text(encoding="utf-8")

        required_markers = [
            "# BL-30.parent.wp2 — Rebuild-vs-Ausbau-Guardrails + API-first Anschluss v1 (Issue #510)",
            "## Rebuild-vs-Ausbau Guardrails je BL-30-Teilstream",
            "## API-first Anschluss für BL-30.2 (testbar, verpflichtend)",
            "### Pflichtmarker (normativ)",
            "### Verifikationspfad vor Merge von #465/#466",
            "## Operative Merge-Policy für BL-30.2",
        ]
        for marker in required_markers:
            self.assertIn(marker, content, msg=f"Marker fehlt in BL-30 Parent Guardrail-Doku: {marker}")

        required_terms = [
            "BL30_API_FIRST_NO_BREAKING_CHANGES",
            "BL30_ENTITLEMENT_SCHEMA_ADDITIVE_ONLY",
            "BL30_CHECKOUT_IDEMPOTENCY_REQUIRED",
            "BL30_RUNTIME_FALLBACK_TO_STANDARD",
            "#465 -> #466",
            "#6, #127",
        ]
        for term in required_terms:
            self.assertIn(term, content, msg=f"Pflichtbegriff fehlt in BL-30 Parent Guardrail-Doku: {term}")

    def test_backlog_references_wp2_completion(self):
        backlog = (REPO_ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")

        self.assertIn(
            "#510 — BL-30.parent.wp2 Rebuild-vs-Ausbau-Guardrails + API-first Anschluss konsolidieren (abgeschlossen 2026-03-01)",
            backlog,
        )
        self.assertIn(
            "[`docs/BL30_REBUILD_VS_AUSBAU_GUARDRAILS_API_FIRST_V1.md`](BL30_REBUILD_VS_AUSBAU_GUARDRAILS_API_FIRST_V1.md)",
            backlog,
        )


if __name__ == "__main__":
    unittest.main()
