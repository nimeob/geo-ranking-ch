import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.compliance.export_logging import build_export_log_entry, record_export_log_entry


class TestComplianceExportLogging(unittest.TestCase):
    def test_build_export_log_entry_contains_required_fields(self):
        payload = build_export_log_entry(
            channel="file:csv",
            artifact_path="reports/exports/sample.csv",
            export_kind="address-intel-batch-csv",
            row_count=12,
            error_count=1,
            status="partial",
            actor="worker-a",
            exported_at_utc="2026-03-01T08:00:00Z",
            details={"scope": "batch-export"},
        )

        self.assertEqual(payload["actor"], "worker-a")
        self.assertEqual(payload["channel"], "file:csv")
        self.assertEqual(payload["exported_at_utc"], "2026-03-01T08:00:00Z")
        self.assertEqual(payload["row_count"], 12)
        self.assertEqual(payload["error_count"], 1)
        self.assertEqual(payload["status"], "partial")
        self.assertEqual(payload["event"], "compliance.export.logged")

    def test_record_export_log_entry_writes_jsonl_and_uses_actor_from_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "export-log.jsonl"

            with patch.dict("os.environ", {"COMPLIANCE_EXPORT_ACTOR": "env-actor"}, clear=False):
                payload = record_export_log_entry(
                    channel="file:jsonl",
                    artifact_path="reports/exports/sample.jsonl",
                    export_kind="address-intel-batch-jsonl",
                    row_count=3,
                    log_path=log_path,
                )

            self.assertEqual(payload["actor"], "env-actor")
            self.assertTrue(log_path.is_file())

            lines = log_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            persisted = json.loads(lines[0])
            self.assertEqual(persisted["channel"], "file:jsonl")
            self.assertEqual(persisted["artifact_path"], "reports/exports/sample.jsonl")
            self.assertIn("exported_at_utc", persisted)

    def test_build_export_log_entry_rejects_empty_channel(self):
        with self.assertRaisesRegex(ValueError, "channel must be a non-empty string"):
            build_export_log_entry(
                channel="  ",
                artifact_path="out.csv",
                export_kind="x",
                row_count=1,
            )


if __name__ == "__main__":
    unittest.main()
