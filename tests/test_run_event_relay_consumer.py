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
    def _event(delivery_id: str, action: str = "labeled") -> dict:
        return {
            "delivery_id": delivery_id,
            "event": "issues",
            "action": action,
            "repository": "nimeob/geo-ranking-ch",
            "target_type": "issue",
            "target_number": 233,
            "labels": ["backlog", "priority:P2"],
            "received_at": "2026-02-27T08:00:00Z",
            "source": "github-webhook",
        }

    @staticmethod
    def _issue(number: int, labels: list[str]) -> dict:
        return {
            "number": number,
            "state": "open",
            "title": f"Issue {number}",
            "labels": labels,
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
            issues_snapshot = tmp / "issues.json"
            issues_snapshot.write_text("[]\n", encoding="utf-8")

            first = self._run(
                "--queue-file",
                str(queue_file),
                "--reports-root",
                str(reports_root),
                "--state-file",
                str(state_file),
                "--schema-path",
                str(SCHEMA_PATH),
                "--issues-snapshot",
                str(issues_snapshot),
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
                "--issues-snapshot",
                str(issues_snapshot),
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

    def test_dispatches_reconcile_for_labeled_event_and_mutates_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            queue_file = tmp / "queue.ndjson"
            queue_file.write_text(json.dumps(self._event("delivery-label", action="labeled")) + "\n", encoding="utf-8")

            issues_snapshot = tmp / "issues.json"
            issues_snapshot.write_text(
                json.dumps(
                    [
                        self._issue(220, ["backlog", "priority:P1", "status:blocked"]),
                        self._issue(233, ["backlog", "priority:P2", "status:todo"]),
                    ],
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
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
                "--issues-snapshot",
                str(issues_snapshot),
                "--timestamp",
                "20260227T080004Z",
                "--mode",
                "apply",
            )

            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            payload = json.loads(completed.stdout.strip())
            self.assertEqual(payload["summary"]["reconcile_dispatch_runs"], 1)
            self.assertEqual(payload["summary"]["reconcile_dispatch_requested"], 1)
            self.assertEqual(payload["summary"]["reconcile_mutations"], 2)

            updated_snapshot = json.loads(issues_snapshot.read_text(encoding="utf-8"))
            labels_by_issue = {item["number"]: set(item["labels"]) for item in updated_snapshot}

            self.assertIn("status:todo", labels_by_issue[220])
            self.assertNotIn("status:blocked", labels_by_issue[220])
            self.assertIn("status:blocked", labels_by_issue[233])
            self.assertNotIn("status:todo", labels_by_issue[233])

    def test_reconcile_handles_labeled_unlabeled_reopened_sequences(self):
        for idx, action in enumerate(["labeled", "unlabeled", "reopened"], start=1):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as tmpdir:
                tmp = Path(tmpdir)
                queue_file = tmp / "queue.ndjson"
                queue_file.write_text(json.dumps(self._event(f"delivery-{action}", action=action)) + "\n", encoding="utf-8")

                issues_snapshot = tmp / "issues.json"
                issues_snapshot.write_text(
                    json.dumps(
                        [
                            self._issue(220, ["backlog", "priority:P1", "status:todo"]),
                            self._issue(233, ["backlog", "priority:P2", "status:blocked"]),
                        ],
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
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
                    "--issues-snapshot",
                    str(issues_snapshot),
                    "--timestamp",
                    f"20260227T08010{idx}Z",
                    "--mode",
                    "apply",
                )

                self.assertEqual(completed.returncode, 0, msg=completed.stderr)
                payload = json.loads(completed.stdout.strip())
                self.assertEqual(payload["summary"]["accepted"], 1)
                self.assertEqual(payload["summary"]["reconcile_dispatch_runs"], 1)
                self.assertEqual(payload["summary"]["reconcile_dispatch_failed"], 0)

    def test_reconcile_keeps_active_in_progress_without_promote_todo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            queue_file = tmp / "queue.ndjson"
            queue_file.write_text(json.dumps(self._event("delivery-in-progress", action="labeled")) + "\n", encoding="utf-8")

            issues_snapshot = tmp / "issues.json"
            issues_snapshot.write_text(
                json.dumps(
                    [
                        self._issue(220, ["backlog", "priority:P1", "status:in-progress"]),
                        self._issue(233, ["backlog", "priority:P2", "status:todo"]),
                    ],
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
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
                "--issues-snapshot",
                str(issues_snapshot),
                "--timestamp",
                "20260227T080150Z",
                "--mode",
                "apply",
            )

            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            payload = json.loads(completed.stdout.strip())
            self.assertEqual(payload["summary"]["reconcile_dispatch_runs"], 1)

            updated_snapshot = json.loads(issues_snapshot.read_text(encoding="utf-8"))
            labels_by_issue = {item["number"]: set(item["labels"]) for item in updated_snapshot}

            self.assertIn("status:in-progress", labels_by_issue[220])
            self.assertNotIn("status:todo", labels_by_issue[220])
            self.assertIn("status:blocked", labels_by_issue[233])
            self.assertNotIn("status:todo", labels_by_issue[233])

    def test_batches_multiple_issue_events_into_single_reconcile_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            queue_file = tmp / "queue.ndjson"
            queue_file.write_text(
                "\n".join(
                    [
                        json.dumps(self._event("delivery-a", action="labeled")),
                        json.dumps(self._event("delivery-b", action="unlabeled")),
                        json.dumps(self._event("delivery-c", action="reopened")),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            issues_snapshot = tmp / "issues.json"
            issues_snapshot.write_text(
                json.dumps(
                    [
                        self._issue(220, ["backlog", "priority:P1", "status:todo"]),
                        self._issue(233, ["backlog", "priority:P2", "status:todo"]),
                    ],
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
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
                "--issues-snapshot",
                str(issues_snapshot),
                "--timestamp",
                "20260227T080200Z",
                "--mode",
                "apply",
            )

            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            payload = json.loads(completed.stdout.strip())
            self.assertEqual(payload["summary"]["accepted"], 3)
            self.assertEqual(payload["summary"]["reconcile_dispatch_requested"], 3)
            self.assertEqual(payload["summary"]["reconcile_dispatch_runs"], 1)


if __name__ == "__main__":
    unittest.main()
