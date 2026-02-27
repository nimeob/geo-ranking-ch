import hashlib
import hmac
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_event_relay_receiver.py"


class TestRunEventRelayReceiver(unittest.TestCase):
    def _run(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        runtime_env = os.environ.copy()
        if env:
            runtime_env.update(env)
        return subprocess.run(
            ["python3", str(SCRIPT_PATH), *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=runtime_env,
        )

    @staticmethod
    def _issue_payload(repo: str = "nimeob/geo-ranking-ch") -> dict:
        return {
            "action": "labeled",
            "repository": {"full_name": repo},
            "issue": {
                "number": 233,
                "labels": [{"name": "backlog"}, {"name": "priority:P2"}],
            },
        }

    @staticmethod
    def _signature(payload_bytes: bytes, secret: str) -> str:
        digest = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
        return f"sha256={digest}"

    def test_accepts_valid_issue_webhook_and_appends_queue(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            queue_file = tmp / "queue.ndjson"
            state_file = tmp / "state" / "delivery_ids.json"
            payload_path = tmp / "payload.json"
            headers_path = tmp / "headers.json"

            payload = self._issue_payload()
            payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            payload_path.write_bytes(payload_bytes)
            headers_path.write_text(
                json.dumps(
                    {
                        "X-GitHub-Event": "issues",
                        "X-GitHub-Delivery": "delivery-001",
                        "X-Hub-Signature-256": self._signature(payload_bytes, "topsecret"),
                    }
                ),
                encoding="utf-8",
            )

            completed = self._run(
                "--headers-file",
                str(headers_path),
                "--payload-file",
                str(payload_path),
                "--queue-file",
                str(queue_file),
                "--state-file",
                str(state_file),
                "--allowed-repositories",
                "nimeob/geo-ranking-ch",
                env={"GITHUB_WEBHOOK_SECRET": "topsecret"},
            )

            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            payload_out = json.loads(completed.stdout.strip())
            self.assertEqual(payload_out["status"], "accepted")
            self.assertEqual(payload_out["event"], "issues")

            queue_lines = queue_file.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(queue_lines), 1)
            envelope = json.loads(queue_lines[0])
            self.assertEqual(envelope["delivery_id"], "delivery-001")
            self.assertEqual(envelope["repository"], "nimeob/geo-ranking-ch")
            self.assertEqual(envelope["target_type"], "issue")
            self.assertEqual(envelope["target_number"], 233)
            self.assertEqual(envelope["labels"], ["backlog", "priority:P2"])

            state = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertIn("delivery-001", state)

    def test_detects_duplicate_delivery_and_skips_second_append(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            queue_file = tmp / "queue.ndjson"
            state_file = tmp / "state" / "delivery_ids.json"
            payload_path = tmp / "payload.json"
            headers_path = tmp / "headers.json"

            payload = self._issue_payload()
            payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            payload_path.write_bytes(payload_bytes)
            headers_path.write_text(
                json.dumps(
                    {
                        "X-GitHub-Event": "issues",
                        "X-GitHub-Delivery": "delivery-dup",
                        "X-Hub-Signature-256": self._signature(payload_bytes, "topsecret"),
                    }
                ),
                encoding="utf-8",
            )

            base_args = [
                "--headers-file",
                str(headers_path),
                "--payload-file",
                str(payload_path),
                "--queue-file",
                str(queue_file),
                "--state-file",
                str(state_file),
                "--allowed-repositories",
                "nimeob/geo-ranking-ch",
            ]

            first = self._run(*base_args, env={"GITHUB_WEBHOOK_SECRET": "topsecret"})
            self.assertEqual(first.returncode, 0, msg=first.stderr)

            second = self._run(*base_args, env={"GITHUB_WEBHOOK_SECRET": "topsecret"})
            self.assertEqual(second.returncode, 0, msg=second.stderr)
            payload_out = json.loads(second.stdout.strip())
            self.assertEqual(payload_out["status"], "duplicate")

            queue_lines = queue_file.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(queue_lines), 1)

    def test_rejects_invalid_signature(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            queue_file = tmp / "queue.ndjson"
            state_file = tmp / "state" / "delivery_ids.json"
            payload_path = tmp / "payload.json"
            headers_path = tmp / "headers.json"

            payload = self._issue_payload()
            payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            payload_path.write_bytes(payload_bytes)
            headers_path.write_text(
                json.dumps(
                    {
                        "X-GitHub-Event": "issues",
                        "X-GitHub-Delivery": "delivery-invalid-signature",
                        "X-Hub-Signature-256": self._signature(payload_bytes, "wrong-secret"),
                    }
                ),
                encoding="utf-8",
            )

            completed = self._run(
                "--headers-file",
                str(headers_path),
                "--payload-file",
                str(payload_path),
                "--queue-file",
                str(queue_file),
                "--state-file",
                str(state_file),
                "--allowed-repositories",
                "nimeob/geo-ranking-ch",
                env={"GITHUB_WEBHOOK_SECRET": "topsecret"},
            )

            self.assertEqual(completed.returncode, 4)
            payload_out = json.loads(completed.stdout.strip())
            self.assertEqual(payload_out["status"], "rejected")
            self.assertEqual(payload_out["reason"], "invalid_signature")
            self.assertFalse(queue_file.exists())

    def test_rejects_repository_outside_allowlist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            queue_file = tmp / "queue.ndjson"
            state_file = tmp / "state" / "delivery_ids.json"
            payload_path = tmp / "payload.json"
            headers_path = tmp / "headers.json"

            payload = self._issue_payload(repo="other-org/foreign-repo")
            payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            payload_path.write_bytes(payload_bytes)
            headers_path.write_text(
                json.dumps(
                    {
                        "X-GitHub-Event": "issues",
                        "X-GitHub-Delivery": "delivery-foreign",
                        "X-Hub-Signature-256": self._signature(payload_bytes, "topsecret"),
                    }
                ),
                encoding="utf-8",
            )

            completed = self._run(
                "--headers-file",
                str(headers_path),
                "--payload-file",
                str(payload_path),
                "--queue-file",
                str(queue_file),
                "--state-file",
                str(state_file),
                "--allowed-repositories",
                "nimeob/geo-ranking-ch",
                env={"GITHUB_WEBHOOK_SECRET": "topsecret"},
            )

            self.assertEqual(completed.returncode, 4)
            payload_out = json.loads(completed.stdout.strip())
            self.assertEqual(payload_out["status"], "rejected")
            self.assertEqual(payload_out["reason"], "repository_not_allowlisted")
            self.assertFalse(queue_file.exists())


if __name__ == "__main__":
    unittest.main()
