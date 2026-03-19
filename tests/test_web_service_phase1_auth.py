import unittest

from src.api.web_service_phase1_auth import (
    Phase1AuthUser,
    load_phase1_auth_users_from_config,
    normalize_phase1_auth_scalar,
    resolve_phase1_auth_user,
)


class TestWebServicePhase1Auth(unittest.TestCase):
    def test_normalize_scalar_rejects_empty_and_controls(self):
        self.assertEqual(normalize_phase1_auth_scalar(" token ", field_name="token"), "token")
        with self.assertRaisesRegex(ValueError, "token must be a non-empty string"):
            normalize_phase1_auth_scalar("  ", field_name="token")
        with self.assertRaisesRegex(ValueError, "token must not contain control characters"):
            normalize_phase1_auth_scalar("ab\ncd", field_name="token")

    def test_load_users_from_inline_json_supports_default_org(self):
        users = load_phase1_auth_users_from_config(
            raw_file="",
            raw_json='{"users":[{"token":"a","user_id":"u1"},{"token":"b","user_id":"u2","org_id":"org-2"}]}'
        )

        self.assertEqual(
            users,
            [
                Phase1AuthUser(token="a", user_id="u1", org_id="u1"),
                Phase1AuthUser(token="b", user_id="u2", org_id="org-2"),
            ],
        )

    def test_load_users_rejects_invalid_shapes(self):
        with self.assertRaisesRegex(ValueError, "must be valid JSON"):
            load_phase1_auth_users_from_config(raw_file="", raw_json="{not json}")

        with self.assertRaisesRegex(ValueError, "must be a list or"):
            load_phase1_auth_users_from_config(raw_file="", raw_json='{"users":{}}')

        with self.assertRaisesRegex(ValueError, "entry #1 must be an object"):
            load_phase1_auth_users_from_config(raw_file="", raw_json='["x"]')

    def test_resolve_phase1_auth_user_matches_exact_token(self):
        users = [
            Phase1AuthUser(token="token-a", user_id="u1", org_id="o1"),
            Phase1AuthUser(token="token-b", user_id="u2", org_id="o2"),
        ]

        self.assertIsNone(resolve_phase1_auth_user("", users))
        self.assertIsNone(resolve_phase1_auth_user("token-c", users))

        matched = resolve_phase1_auth_user("token-b", users)
        self.assertIsNotNone(matched)
        assert matched is not None
        self.assertEqual(matched.user_id, "u2")
        self.assertEqual(matched.org_id, "o2")


if __name__ == "__main__":
    unittest.main()
