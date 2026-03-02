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


if __name__ == "__main__":
    unittest.main()
