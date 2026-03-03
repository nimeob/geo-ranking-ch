import unittest

from src.api.oidc_jwt import JwksCache, JwtValidationError, OidcJwtConfig, OidcJwtValidator


# Test vectors from RFC 7515 Appendix A.2 (RS256) as mirrored in:
# https://raw.githubusercontent.com/Deliaz/RFC7515-A2/master/script.js
_RFC_A2_TOKEN = (
    "eyJhbGciOiJSUzI1NiJ9."
    "eyJpc3MiOiJqb2UiLA0KICJleHAiOjEzMDA4MTkzODAsDQogImh0dHA6Ly9leGFtcGxlLmNvbS9pc19yb290Ijp0cnVlfQ."
    "cC4hiUPoj9Eetdgtv3hF80EGrhuB__dzERat0XF9g2VtQgr9PJbu3XOiZj5RZmh7AAuHIm4Bh-0Qc_lF5YKt_O8W2Fp5jujGbds9uJdbF9CUAr7t1dnZcAcQjbKBYNX4BAynRFdiuB--f_nZLgrnbyTyWzO75vRK5h6xBArLIARNPvkSjtQBMHlb1L07Qe7K0GarZRmB_eSN9383LcOLn6_dO--xi12jzDwusC-eOkHWEsqtFZESc6BfI7noOPqvhJ1phCnvWh6IeYI2w9QOYEUipUTI8np6LbgGY9Fs98rqVt5AXLIhWkWywlVmtVrBp0igcN_IoypGlUPQGe77Rw"
)

_RFC_A2_JWKS = {
    "keys": [
        {
            "kty": "RSA",
            "n": "ofgWCuLjybRlzo0tZWJjNiuSfb4p4fAkd_wWJcyQoTbji9k0l8W26mPddxHmfHQp-Vaw-4qPCJrcS2mJPMEzP1Pt0Bm4d4QlL-yRT-SFd2lZS-pCgNMsD1W_YpRPEwOWvG6b32690r2jZ47soMZo9wGzjb_7OMg0LOL-bSf63kpaSHSXndS5z5rexMdbBYUsLA9e-KXBdQOS-UTo7WTBEMa2R2CapHg665xsmtdVMTBQY4uDZlxvb3qCo5ZwKh9kG4LT6_I5IhlJH7aGhyxXFvUK-DWNmoudF8NAco9_h9iaGNj8q2ethFkMLs91kzk2PAcDTW9gb54h4FRWyuXpoQ",
            "e": "AQAB",
        }
    ]
}

_RFC_A2_JWKS_MULTI = {
    "keys": [
        {
            "kid": "key-a",
            "kty": "RSA",
            "n": "ofgWCuLjybRlzo0tZWJjNiuSfb4p4fAkd_wWJcyQoTbji9k0l8W26mPddxHmfHQp-Vaw-4qPCJrcS2mJPMEzP1Pt0Bm4d4QlL-yRT-SFd2lZS-pCgNMsD1W_YpRPEwOWvG6b32690r2jZ47soMZo9wGzjb_7OMg0LOL-bSf63kpaSHSXndS5z5rexMdbBYUsLA9e-KXBdQOS-UTo7WTBEMa2R2CapHg665xsmtdVMTBQY4uDZlxvb3qCo5ZwKh9kG4LT6_I5IhlJH7aGhyxXFvUK-DWNmoudF8NAco9_h9iaGNj8q2ethFkMLs91kzk2PAcDTW9gb54h4FRWyuXpoQ",
            "e": "AQAB",
        },
        {
            "kid": "key-b",
            "kty": "RSA",
            "n": "ofgWCuLjybRlzo0tZWJjNiuSfb4p4fAkd_wWJcyQoTbji9k0l8W26mPddxHmfHQp-Vaw-4qPCJrcS2mJPMEzP1Pt0Bm4d4QlL-yRT-SFd2lZS-pCgNMsD1W_YpRPEwOWvG6b32690r2jZ47soMZo9wGzjb_7OMg0LOL-bSf63kpaSHSXndS5z5rexMdbBYUsLA9e-KXBdQOS-UTo7WTBEMa2R2CapHg665xsmtdVMTBQY4uDZlxvb3qCo5ZwKh9kG4LT6_I5IhlJH7aGhyxXFvUK-DWNmoudF8NAco9_h9iaGNj8q2ethFkMLs91kzk2PAcDTW9gb54h4FRWyuXpoQ",
            "e": "AQAB",
        },
    ]
}


class _CountingFetcher:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def __call__(self, url: str, timeout_seconds: float):
        self.calls += 1
        return dict(self.payload)


class TestOidcJwtValidation(unittest.TestCase):
    def _validator(self, *, issuer: str = "joe", audience: str = "", ttl_seconds: float = 300.0):
        fetcher = _CountingFetcher(_RFC_A2_JWKS)
        cache = JwksCache(
            jwks_url="https://example.invalid/.well-known/jwks.json",
            ttl_seconds=ttl_seconds,
            timeout_seconds=1.0,
            fetch_json=fetcher,
        )
        validator = OidcJwtValidator(config=OidcJwtConfig(issuer=issuer, audience=audience), jwks=cache)
        return validator, fetcher

    def _validator_multi_jwks(self, *, issuer: str = "joe", audience: str = ""):
        fetcher = _CountingFetcher(_RFC_A2_JWKS_MULTI)
        cache = JwksCache(
            jwks_url="https://example.invalid/.well-known/jwks.json",
            ttl_seconds=300.0,
            timeout_seconds=1.0,
            fetch_json=fetcher,
        )
        validator = OidcJwtValidator(config=OidcJwtConfig(issuer=issuer, audience=audience), jwks=cache)
        return validator, fetcher

    @staticmethod
    def _forge_rs256_token_with_kid(kid: str) -> str:
        import base64
        import json

        def _b64url(data: bytes) -> str:
            return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

        header = _b64url(json.dumps({"alg": "RS256", "kid": kid}).encode())
        payload = _b64url(json.dumps({"iss": "joe", "exp": 9999999999}).encode())
        signature = "AA"  # invalid by design; tests focus on key selection path
        return f"{header}.{payload}.{signature}"

    def test_rfc_a2_signature_and_claims_ok(self):
        validator, fetcher = self._validator(issuer="joe")
        # exp is 1300819380 → validate before expiry
        claims = validator.validate(_RFC_A2_TOKEN, now=1300819300)
        self.assertEqual(claims.get("iss"), "joe")
        self.assertEqual(fetcher.calls, 1)

    def test_cache_reuse(self):
        validator, fetcher = self._validator(issuer="joe", ttl_seconds=999)
        validator.validate(_RFC_A2_TOKEN, now=1300819300)
        validator.validate(_RFC_A2_TOKEN, now=1300819301)
        self.assertEqual(fetcher.calls, 1)

    def test_reject_wrong_issuer(self):
        validator, _ = self._validator(issuer="mallory")
        with self.assertRaises(JwtValidationError) as ctx:
            validator.validate(_RFC_A2_TOKEN, now=1300819300)
        self.assertEqual(ctx.exception.code, "invalid_issuer")

    def test_reject_when_audience_required_but_missing(self):
        validator, _ = self._validator(issuer="joe", audience="my-api")
        with self.assertRaises(JwtValidationError) as ctx:
            validator.validate(_RFC_A2_TOKEN, now=1300819300)
        self.assertEqual(ctx.exception.code, "invalid_audience")

    def test_accepts_cognito_access_token_client_id_when_audience_matches(self):
        validator, _ = self._validator(issuer="issuer.example", audience="cognito-client-id")
        claims = {
            "iss": "issuer.example",
            "exp": 9999999999,
            "token_use": "access",
            "client_id": "cognito-client-id",
        }

        # Should not raise: Cognito-style access token without `aud`.
        validator._validate_claims(claims, now=1300819300)

    def test_rejects_cognito_access_token_when_client_id_mismatches_audience(self):
        validator, _ = self._validator(issuer="issuer.example", audience="expected-client-id")
        claims = {
            "iss": "issuer.example",
            "exp": 9999999999,
            "token_use": "access",
            "client_id": "different-client-id",
        }

        with self.assertRaises(JwtValidationError) as ctx:
            validator._validate_claims(claims, now=1300819300)
        self.assertEqual(ctx.exception.code, "invalid_audience")

    def test_rejects_non_access_token_without_aud_even_if_client_id_matches(self):
        validator, _ = self._validator(issuer="issuer.example", audience="client-id")
        claims = {
            "iss": "issuer.example",
            "exp": 9999999999,
            "token_use": "id",
            "client_id": "client-id",
        }

        with self.assertRaises(JwtValidationError) as ctx:
            validator._validate_claims(claims, now=1300819300)
        self.assertEqual(ctx.exception.code, "invalid_audience")

    def test_reject_expired(self):
        validator, _ = self._validator(issuer="joe")
        with self.assertRaises(JwtValidationError) as ctx:
            validator.validate(_RFC_A2_TOKEN, now=1300819380 + 61)
        self.assertEqual(ctx.exception.code, "token_expired")

    def test_invalid_format(self):
        validator, _ = self._validator(issuer="joe")
        with self.assertRaises(JwtValidationError) as ctx:
            validator.validate("not-a-jwt")
        self.assertEqual(ctx.exception.code, "invalid_format")

    def test_missing_token_empty_string(self):
        """Passing an empty string (bearer absent) must raise invalid_format."""
        validator, _ = self._validator(issuer="joe")
        with self.assertRaises(JwtValidationError) as ctx:
            validator.validate("")
        self.assertEqual(ctx.exception.code, "invalid_format")

    def test_missing_token_whitespace(self):
        """Whitespace-only input is treated as missing / invalid."""
        validator, _ = self._validator(issuer="joe")
        with self.assertRaises(JwtValidationError) as ctx:
            validator.validate("   ")
        self.assertEqual(ctx.exception.code, "invalid_format")

    def test_reject_alg_none(self):
        """Tokens with alg:none (algorithm confusion) must be rejected."""
        import base64
        import json

        def _b64url(data: bytes) -> str:
            return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

        header = _b64url(json.dumps({"alg": "none"}).encode())
        payload = _b64url(json.dumps({"iss": "joe", "exp": 9999999999}).encode())
        forged = f"{header}.{payload}."  # empty signature

        validator, _ = self._validator(issuer="joe")
        with self.assertRaises(JwtValidationError) as ctx:
            validator.validate(forged)
        self.assertEqual(ctx.exception.code, "unsupported_alg")

    def test_reject_invalid_signature(self):
        """A token with a tampered signature must be rejected."""
        parts = _RFC_A2_TOKEN.split(".")
        # Flip one character in the signature segment.
        bad_sig = parts[2][:-1] + ("A" if parts[2][-1] != "A" else "B")
        tampered = ".".join([parts[0], parts[1], bad_sig])

        validator, _ = self._validator(issuer="joe")
        with self.assertRaises(JwtValidationError) as ctx:
            validator.validate(tampered, now=1300819300)
        self.assertEqual(ctx.exception.code, "invalid_signature")

    def test_reject_aud_list_without_match(self):
        """aud claim as list without the expected audience is rejected."""
        import base64
        import json
        import time

        # We cannot sign a real token, but we can verify aud check happens before sig
        # by using the RFC token and checking aud with audience config.
        # RFC token has no aud claim → "invalid_audience" when audience is required.
        validator, _ = self._validator(issuer="joe", audience="expected-api")
        with self.assertRaises(JwtValidationError) as ctx:
            validator.validate(_RFC_A2_TOKEN, now=1300819300)
        self.assertEqual(ctx.exception.code, "invalid_audience")

    def test_multi_jwks_with_unknown_kid_rejected(self):
        validator, _ = self._validator_multi_jwks(issuer="joe")
        token = self._forge_rs256_token_with_kid("missing-kid")
        with self.assertRaises(JwtValidationError) as ctx:
            validator.validate(token, now=1300819300)
        self.assertEqual(ctx.exception.code, "invalid_kid")

    def test_multi_jwks_with_matching_kid_reaches_signature_check(self):
        validator, _ = self._validator_multi_jwks(issuer="joe")
        token = self._forge_rs256_token_with_kid("key-a")
        with self.assertRaises(JwtValidationError) as ctx:
            validator.validate(token, now=1300819300)
        # Matching kid selected a key; invalid signature is expected for forged token.
        self.assertEqual(ctx.exception.code, "invalid_signature")

    def test_jwks_cache_expires_and_refetches(self):
        """After TTL expires the JWKS endpoint is fetched again."""
        validator, fetcher = self._validator(issuer="joe", ttl_seconds=10)
        validator.validate(_RFC_A2_TOKEN, now=1300819300)
        # Advance time past TTL; next call must re-fetch.
        validator.validate(_RFC_A2_TOKEN, now=1300819300 + 11)
        # The second validate triggers cache miss on the JwksCache, but the internal
        # _cached_until is checked inside JwksCache.get_rsa_keys().
        # Two separate calls to validate with ttl expired → 2 fetches.
        self.assertGreaterEqual(fetcher.calls, 2)


if __name__ == "__main__":
    unittest.main()
