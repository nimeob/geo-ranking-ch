import unittest

from src.api.web_service_oidc_loader import load_oidc_jwt_validator_from_env


class TestWebServiceOidcLoader(unittest.TestCase):
    def test_returns_none_when_jwks_url_missing(self):
        env = {}
        validator = load_oidc_jwt_validator_from_env(env_getter=lambda key, default="": env.get(key, default))
        self.assertIsNone(validator)

    def test_builds_validator_from_env_values(self):
        env = {
            "OIDC_JWKS_URL": "https://example.test/.well-known/jwks.json",
            "OIDC_JWT_ISSUER": "https://issuer.example.test",
            "OIDC_JWT_AUDIENCE": "geo-ranking-api",
            "OIDC_JWKS_TTL_SECONDS": "120",
            "OIDC_JWKS_TIMEOUT_SECONDS": "4.5",
            "OIDC_CLOCK_SKEW_SECONDS": "30",
        }

        validator = load_oidc_jwt_validator_from_env(env_getter=lambda key, default="": env.get(key, default))
        self.assertIsNotNone(validator)
        assert validator is not None
        self.assertEqual(validator.config.issuer, "https://issuer.example.test")
        self.assertEqual(validator.config.audience, "geo-ranking-api")
        self.assertEqual(validator.config.clock_skew_seconds, 30.0)
        self.assertEqual(validator.jwks.jwks_url, "https://example.test/.well-known/jwks.json")
        self.assertEqual(validator.jwks.ttl_seconds, 120.0)
        self.assertEqual(validator.jwks.timeout_seconds, 4.5)

    def test_supports_legacy_issuer_audience_aliases(self):
        env = {
            "OIDC_JWKS_URL": "https://example.test/.well-known/jwks.json",
            "OIDC_ISSUER": "https://legacy-issuer.example.test",
            "OIDC_AUDIENCE": "legacy-audience",
        }

        validator = load_oidc_jwt_validator_from_env(env_getter=lambda key, default="": env.get(key, default))
        self.assertIsNotNone(validator)
        assert validator is not None
        self.assertEqual(validator.config.issuer, "https://legacy-issuer.example.test")
        self.assertEqual(validator.config.audience, "legacy-audience")

    def test_prefers_oidc_jwt_env_names_over_legacy_aliases(self):
        env = {
            "OIDC_JWKS_URL": "https://example.test/.well-known/jwks.json",
            "OIDC_JWT_ISSUER": "https://primary-issuer.example.test",
            "OIDC_JWT_AUDIENCE": "primary-audience",
            "OIDC_ISSUER": "https://legacy-issuer.example.test",
            "OIDC_AUDIENCE": "legacy-audience",
        }

        validator = load_oidc_jwt_validator_from_env(env_getter=lambda key, default="": env.get(key, default))
        self.assertIsNotNone(validator)
        assert validator is not None
        self.assertEqual(validator.config.issuer, "https://primary-issuer.example.test")
        self.assertEqual(validator.config.audience, "primary-audience")

    def test_rejects_invalid_numeric_env_values(self):
        env_ttl = {
            "OIDC_JWKS_URL": "https://example.test/jwks.json",
            "OIDC_JWKS_TTL_SECONDS": "abc",
        }
        with self.assertRaisesRegex(ValueError, "OIDC_JWKS_TTL_SECONDS must be a number"):
            load_oidc_jwt_validator_from_env(env_getter=lambda key, default="": env_ttl.get(key, default))

        env_timeout = {
            "OIDC_JWKS_URL": "https://example.test/jwks.json",
            "OIDC_JWKS_TIMEOUT_SECONDS": "0",
        }
        with self.assertRaisesRegex(ValueError, "OIDC_JWKS_TIMEOUT_SECONDS must be finite and > 0"):
            load_oidc_jwt_validator_from_env(env_getter=lambda key, default="": env_timeout.get(key, default))


if __name__ == "__main__":
    unittest.main()
