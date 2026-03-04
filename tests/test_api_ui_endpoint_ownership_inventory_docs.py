from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "api" / "API_UI_ENDPOINT_OWNERSHIP_INVENTORY.md"


class TestApiUiEndpointOwnershipInventoryDocs(unittest.TestCase):
    def _table_rows(self) -> list[list[str]]:
        content = DOC_PATH.read_text(encoding="utf-8")
        start_marker = "<!-- ENDPOINT_INVENTORY:START -->"
        end_marker = "<!-- ENDPOINT_INVENTORY:END -->"
        self.assertIn(start_marker, content)
        self.assertIn(end_marker, content)

        block = content.split(start_marker, 1)[1].split(end_marker, 1)[0]
        rows: list[list[str]] = []
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            # header / separator
            if stripped.startswith("| Endpoint") or stripped.startswith("|---"):
                continue
            parts = [part.strip() for part in stripped.strip("|").split("|")]
            if len(parts) != 7:
                continue
            rows.append(parts)
        return rows

    def test_inventory_doc_exists_and_has_required_rows(self) -> None:
        self.assertTrue(DOC_PATH.is_file(), msg="Endpoint-Inventory-Dokument fehlt")
        rows = self._table_rows()
        self.assertGreaterEqual(len(rows), 20, msg="Endpoint-Inventar wirkt unvollständig")

        endpoints = {row[0] for row in rows}
        expected = {
            "`/`",
            "`/gui`",
            "`/history`",
            "`/results/<result_id>`",
            "`/jobs`",
            "`/jobs/<job_id>`",
            "`/auth/login`",
            "`/auth/callback`",
            "`/auth/logout`",
            "`/auth/me`",
            "`/health`",
            "`/healthz`",
            "`/health/details`",
            "`/version`",
            "`/analyze`",
            "`/analyze/history`",
            "`/analyze/jobs/<job_id>`",
            "`/analyze/jobs/<job_id>/notifications`",
            "`/analyze/jobs/<job_id>/cancel`",
            "`/analyze/results/<result_id>`",
            "`/api/v1/dictionaries`",
            "`/api/v1/dictionaries/<domain>`",
            "`/trace` (legacy alias)",
            "`/debug/trace`",
            "`/compliance/corrections/<document_id>`",
        }
        self.assertTrue(expected.issubset(endpoints), msg="Nicht alle Kern-Endpunkte sind inventarisiert")

    def test_rows_have_valid_class_owner_and_priority(self) -> None:
        rows = self._table_rows()
        valid_classes = {"DATA", "UI", "MIXED"}

        for endpoint, _method, _runtime, klass, owner, priority, _note in rows:
            self.assertIn(klass, valid_classes, msg=f"Ungültige Klasse bei {endpoint}")
            self.assertTrue(owner and "tbd" not in owner.lower(), msg=f"Owner fehlt bei {endpoint}")
            self.assertRegex(priority, r"^[1-4]$", msg=f"Ungültige Priorität bei {endpoint}")


if __name__ == "__main__":
    unittest.main()
