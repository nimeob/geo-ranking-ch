import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "sync_backlog_issue_status.py"


def _load_module():
    module_name = "sync_backlog_issue_status"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class TestSyncBacklogIssueStatus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module()

    def test_sync_checkboxes_uses_issue_state(self):
        text = """
- [ ] #10 — open item
- [x] #11 — closed item
- [ ] #12 — unknown
""".lstrip()
        synced, updates = self.module.sync_checkboxes(
            text,
            {
                10: "OPEN",
                11: "CLOSED",
                12: "CLOSED",
            },
        )

        self.assertEqual(updates, 1)
        self.assertIn("- [ ] #10", synced)
        self.assertIn("- [x] #11", synced)
        self.assertIn("- [x] #12", synced)

    def test_render_now_next_later_board_classifies_lanes(self):
        issues = [
            {
                "number": 1,
                "title": "Active",
                "url": "https://example/1",
                "createdAt": "2026-03-01T00:00:00Z",
                "labels": [{"name": "backlog"}, {"name": "status:in-progress"}, {"name": "priority:P1"}],
            },
            {
                "number": 2,
                "title": "Todo P1",
                "url": "https://example/2",
                "createdAt": "2026-03-01T00:00:01Z",
                "labels": [{"name": "backlog"}, {"name": "status:todo"}, {"name": "priority:P1"}],
            },
            {
                "number": 3,
                "title": "Blocked",
                "url": "https://example/3",
                "createdAt": "2026-03-01T00:00:02Z",
                "labels": [{"name": "backlog"}, {"name": "status:blocked"}, {"name": "priority:P0"}],
            },
        ]

        board = self.module.render_now_next_later_board(issues)
        self.assertIn("### Now", board)
        self.assertIn("[#1](https://example/1)", board)
        self.assertIn("### Next", board)
        self.assertIn("[#2](https://example/2)", board)
        self.assertIn("### Later", board)
        self.assertIn("[#3](https://example/3)", board)

    def test_sync_backlog_text_replaces_marker_block(self):
        backlog = """
Header
<!-- NOW_NEXT_LATER:START -->
old content
<!-- NOW_NEXT_LATER:END -->

- [ ] #5 item
""".lstrip()
        synced, stats = self.module.sync_backlog_text(
            backlog,
            issues_all=[{"number": 5, "state": "CLOSED"}],
            issues_open=[],
        )

        self.assertGreaterEqual(stats.checkbox_updates, 1)
        self.assertTrue(stats.board_updated)
        self.assertIn("## Now / Next / Later (auto-synced)", synced)
        self.assertIn("- [x] #5 item", synced)


if __name__ == "__main__":
    unittest.main()
