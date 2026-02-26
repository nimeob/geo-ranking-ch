import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "blocker_retry_supervisor.py"

spec = importlib.util.spec_from_file_location("blocker_retry_supervisor", SCRIPT_PATH)
supervisor = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(supervisor)


class TestBlockerRetrySupervisor(unittest.TestCase):
    def test_external_fail_comments_matches_timeout_and_reachability(self):
        comments = [
            {"body": "alles gut"},
            {"body": "curl exit 28 while reaching endpoint"},
            {"body": "Connection timed out after 45000 milliseconds"},
            {"body": "Kein erreichbarer öffentlicher Endpoint vorhanden"},
        ]

        failed = supervisor.external_fail_comments(comments)

        self.assertEqual(len(failed), 3)

    def test_has_followup_comment_requires_bot_prefix_and_issue_reference(self):
        comments = [
            {
                "user": {"login": "random-user"},
                "body": "Follow-up issue #200 erstellt",
            },
            {
                "user": {"login": "nipa-openclaw[bot]"},
                "body": "Retry-Supervisor: Follow-up issue #201 erstellt",
            },
        ]

        self.assertTrue(supervisor.has_followup_comment(comments))

    def test_process_issue_after_grace_sets_todo_and_comments(self):
        created_at = "2026-02-26T18:00:00Z"
        issue = {"number": 4}
        comments = [{"body": "curl exit 28 timeout", "created_at": created_at}]
        now = datetime(2026, 2, 26, 22, 5, tzinfo=timezone.utc)

        with patch.object(supervisor, "get_comments", return_value=comments):
            with patch.object(supervisor, "now_utc", return_value=now):
                with patch.object(supervisor, "set_todo") as mocked_set_todo:
                    with patch.object(supervisor, "add_comment") as mocked_add_comment:
                        supervisor.process_issue(issue)

        mocked_set_todo.assert_called_once_with(4)
        mocked_add_comment.assert_called_once()
        self.assertIn("Retry-Versuch 2/3", mocked_add_comment.call_args[0][1])

    def test_process_issue_before_grace_does_nothing(self):
        created_at = "2026-02-26T20:00:00Z"
        issue = {"number": 4}
        comments = [{"body": "connection timed out", "created_at": created_at}]
        now = datetime(2026, 2, 26, 21, 0, tzinfo=timezone.utc)

        with patch.object(supervisor, "get_comments", return_value=comments):
            with patch.object(supervisor, "now_utc", return_value=now):
                with patch.object(supervisor, "set_todo") as mocked_set_todo:
                    with patch.object(supervisor, "add_comment") as mocked_add_comment:
                        supervisor.process_issue(issue)

        mocked_set_todo.assert_not_called()
        mocked_add_comment.assert_not_called()

    def test_process_issue_three_fails_creates_followup_once(self):
        issue = {"number": 4}
        comments = [
            {"body": "curl exit 28", "created_at": "2026-02-26T18:00:00Z"},
            {"body": "timeout", "created_at": "2026-02-26T19:00:00Z"},
            {"body": "service unavailable", "created_at": "2026-02-26T20:00:00Z"},
        ]

        with patch.object(supervisor, "get_comments", return_value=comments):
            with patch.object(supervisor, "has_followup_comment", return_value=False):
                with patch.object(supervisor, "create_followup") as mocked_create_followup:
                    supervisor.process_issue(issue)

        mocked_create_followup.assert_called_once_with(4, 3, "2026-02-26T20:00:00+00:00")

    def test_process_issue_three_fails_skips_when_followup_already_exists(self):
        issue = {"number": 4}
        comments = [
            {"body": "curl exit 28", "created_at": "2026-02-26T18:00:00Z"},
            {"body": "timeout", "created_at": "2026-02-26T19:00:00Z"},
            {"body": "service unavailable", "created_at": "2026-02-26T20:00:00Z"},
            {
                "user": {"login": "nipa-openclaw[bot]"},
                "body": "Follow-up issue #123 erstellt",
                "created_at": "2026-02-26T20:30:00Z",
            },
        ]

        with patch.object(supervisor, "get_comments", return_value=comments):
            with patch.object(supervisor, "has_followup_comment", return_value=True):
                with patch.object(supervisor, "create_followup") as mocked_create_followup:
                    supervisor.process_issue(issue)

        mocked_create_followup.assert_not_called()


if __name__ == "__main__":
    unittest.main()
