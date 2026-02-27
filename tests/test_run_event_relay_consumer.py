import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_event_relay_consumer.py"
SCHEMA_PATH = REPO_ROOT / "docs" / "automation" / "event-relay-envelope.schema.json"


class TestRunEventRelayConsumer(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT_PATH), *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    @staticmethod
    def _event(delivery_id: str) -> dict:
        return {
            "delivery_id": delivery_id,
            "event": "issues",
            "action": "labeled",
            "repository": "nimeob/geo-ranking-ch",
            "target_type": "issue",
            "target_number": 233,
            "labels": ["backlog", "priority:P2"],
            "received_at": "2026-02-27T08:00:00Z",
            "source": "github-webhook",
        }

    def test_writes_reports_and_state_for_valid_queue(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            queue_file = tmp / "queue.ndjson"
            queue_file.write_text(json.dumps(self._event("delivery-001")) + "\n", encoding="utf-8")

            reports_root = tmp / "reports"
            state_file = tmp / "state" / "delivery_ids.json"

            completed = self._run(
                "--queue-file",
                str(queue_file),
                "--reports-root",
                str(reports_root),
                "--state-file",
                str(state_file),
                "--schema-path",
                str(SCHEMA_PATH),
                "--timestamp",
                "20260227T080000Z",
            )

            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            payload = json.loads(completed.stdout.strip())
            self.assertEqual(payload["summary"]["accepted"], 1)
            self.assertEqual(payload["summary"]["duplicates"], 0)
            self.assertEqual(payload["summary"]["invalid"], 0)

            history_json = Path(payload["history_json"])
            latest_json = Path(payload["latest_json"])
            self.assertTrue(history_json.is_file())
            self.assertTrue(latest_json.is_file())

            report = json.loads(history_json.read_text(encoding="utf-8"))
            self.assertEqual(report["summary"]["accepted"], 1)
            self.assertEqual(report["events"][0]["status"], "accepted")

            state = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertIn("delivery-001", state)

    def test_marks_duplicate_delivery_ids_using_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            queue_file = tmp / "queue.ndjson"
            queue_file.write_text(json.dumps(self._event("delivery-dup")) + "\n", encoding="utf-8")

            reports_root = tmp / "reports"
            state_file = tmp / "state" / "delivery_ids.json"

            first = self._run(
                "--queue-file",
                str(queue_file),
                "--reports-root",
                str(reports_root),
                "--state-file",
                str(state_file),
                "--schema-path",
                str(SCHEMA_PATH),
                "--timestamp",
                "20260227T080001Z",
                "--mode",
                "apply",
            )
            self.assertEqual(first.returncode, 0, msg=first.stderr)

            second = self._run(
                "--queue-file",
                str(queue_file),
                "--reports-root",
                str(reports_root),
                "--state-file",
                str(state_file),
                "--schema-path",
                str(SCHEMA_PATH),
                "--timestamp",
                "20260227T080002Z",
                "--mode",
                "apply",
            )

            self.assertEqual(second.returncode, 0, msg=second.stderr)
            payload = json.loads(second.stdout.strip())
            self.assertEqual(payload["summary"]["accepted"], 0)
            self.assertEqual(payload["summary"]["duplicates"], 1)
            self.assertEqual(payload["summary"]["invalid"], 0)

    def test_tracks_invalid_events_without_crashing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            queue_file = tmp / "queue.ndjson"
            invalid_event = {
                "delivery_id": "delivery-invalid",
                "event": "issues",
                "repository": "nimeob/geo-ranking-ch",
                "target_type": "issue",
                "target_number": 1,
                "labels": [],
                "received_at": "2026-02-27T08:00:00Z",
            }
            queue_file.write_text(
                "{not-json}\n" + json.dumps(invalid_event) + "\n",
                encoding="utf-8",
            )

            completed = self._run(
                "--queue-file",
                str(queue_file),
                "--reports-root",
                str(tmp / "reports"),
                "--state-file",
                str(tmp / "state" / "delivery_ids.json"),
                "--schema-path",
                str(SCHEMA_PATH),
                "--timestamp",
                "20260227T080003Z",
            )

            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            payload = json.loads(completed.stdout.strip())
            self.assertEqual(payload["summary"]["invalid"], 2)
            self.assertEqual(payload["summary"]["accepted"], 0)

    def test_fails_when_queue_file_is_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            completed = self._run(
                "--queue-file",
                str(Path(tmpdir) / "missing.ndjson"),
                "--schema-path",
                str(SCHEMA_PATH),
            )

            self.assertEqual(completed.returncode, 2)
            self.assertIn("queue file not found", completed.stderr)


if __name__ == "__main__":
    unittest.main()
