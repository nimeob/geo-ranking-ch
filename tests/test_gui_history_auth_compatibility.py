import unittest

from src.shared.gui_mvp import render_gui_mvp_html


class TestGuiHistoryAuthCompatibility(unittest.TestCase):
    def test_history_panel_accepts_401_and_403_migration_signals(self) -> None:
        body = render_gui_mvp_html(app_version="test")

        self.assertIn("if (response.status === 401 || response.status === 403) {", body)
        self.assertIn("if (response.status === 401) {", body)
        self.assertIn(
            "historyPanelFetchCompatibilityNotice = HISTORY_AUTH_MIGRATION_NOTICE;",
            body,
        )


if __name__ == "__main__":
    unittest.main()
