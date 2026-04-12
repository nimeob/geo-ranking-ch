import unittest

from src.shared.gui_mvp import render_gui_mvp_html


class TestGuiAuthMeCompatibility(unittest.TestCase):
    def test_auth_me_refresh_treats_401_and_403_as_unauthenticated(self) -> None:
        body = render_gui_mvp_html(app_version="test")

        self.assertIn("if (response.status === 401 || response.status === 403) {", body)
        self.assertIn(
            "authState.nextUnauthenticatedPollAtMs = Date.now() + AUTH_UNAUTHENTICATED_BACKGROUND_POLL_COOLDOWN_MS;",
            body,
        )


if __name__ == "__main__":
    unittest.main()
