import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.api import address_intel


class TestAddressIntelExportLogging(unittest.TestCase):
    def test_batch_export_outputs_emit_compliance_log_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            batch_csv = tmp_path / "input.csv"
            batch_csv.write_text("address\nTeststrasse 1, 9000 St. Gallen\n", encoding="utf-8")

            out_jsonl = tmp_path / "out.jsonl"
            out_csv = tmp_path / "out.csv"
            out_error_csv = tmp_path / "out.errors.csv"
            export_log = tmp_path / "export-log.jsonl"

            ok_row = {
                "query": "Teststrasse 1, 9000 St. Gallen",
                "batch_meta": {"row": 1, "status": "ok"},
                "summary_compact": {
                    "matched_address": "Teststrasse 1, 9000 St. Gallen",
                    "confidence": {"score": 88, "level": "high"},
                    "executive": {
                        "needs_review": False,
                        "ambiguity_level": "none",
                        "ambiguity_gap": 42,
                        "warnings": [],
                    },
                    "intelligence": {
                        "mode": "basic",
                        "executive_risk": {"traffic_light": "green", "risk_score": 12, "reasons": []},
                    },
                    "energie": {"heizung": "Fernwärme", "warmwasser": "Fernwärme"},
                    "sources": {"gwr": "ok"},
                    "map": "",
                },
            }
            error_row = address_intel.normalize_error_row(
                "Badstrasse 2, 9000 St. Gallen",
                2,
                ValueError("invalid input"),
            )

            fake_batch = {
                "rows": [ok_row, error_row],
                "stats": {"processed": 2, "ok": 1, "error": 1, "skipped_empty": 0},
            }

            with patch("src.api.address_intel.run_batch", return_value=fake_batch):
                with patch.dict(
                    os.environ,
                    {
                        "COMPLIANCE_EXPORT_LOG_PATH": str(export_log),
                        "COMPLIANCE_EXPORT_ACTOR": "worker-a-test",
                    },
                    clear=False,
                ):
                    argv = [
                        "address_intel.py",
                        "--batch-csv",
                        str(batch_csv),
                        "--out-jsonl",
                        str(out_jsonl),
                        "--out-csv",
                        str(out_csv),
                        "--out-error-csv",
                        str(out_error_csv),
                    ]
                    with patch("sys.argv", argv):
                        rc = address_intel.main()

            self.assertEqual(rc, address_intel.EXIT_BATCH_PARTIAL)
            self.assertTrue(out_jsonl.is_file())
            self.assertTrue(out_csv.is_file())
            self.assertTrue(out_error_csv.is_file())
            self.assertTrue(export_log.is_file())

            entries = [json.loads(line) for line in export_log.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(entries), 3)

            channels = {entry["channel"] for entry in entries}
            self.assertEqual(channels, {"file:jsonl", "file:csv", "file:error-csv"})

            for entry in entries:
                self.assertEqual(entry["actor"], "worker-a-test")
                self.assertIn("exported_at_utc", entry)
                self.assertEqual(entry["event"], "compliance.export.logged")


if __name__ == "__main__":
    unittest.main()
