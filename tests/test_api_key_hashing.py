from __future__ import annotations

import hashlib
import hmac
import unittest

from src.shared.api_key_hashing import (
    DEFAULT_HASH_SCHEME,
    build_api_key_storage_fields,
    build_key_fingerprint,
    hash_api_key,
    verify_api_key,
)


class TestApiKeyHashing(unittest.TestCase):
    def test_build_key_fingerprint_returns_stable_hex_prefix(self) -> None:
        token = "tok_123"
        expected = hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]
        self.assertEqual(build_key_fingerprint(token), expected)

    def test_hash_api_key_hmac_sha256_matches_reference(self) -> None:
        token = "tok_123"
        secret = b"unit-test-secret"

        expected = hmac.new(secret, token.encode("utf-8"), hashlib.sha256).hexdigest()
        self.assertEqual(hash_api_key(token, secret=secret, scheme=DEFAULT_HASH_SCHEME), expected)

    def test_verify_api_key_roundtrip(self) -> None:
        token = "tok_123"
        secret = b"unit-test-secret"
        stored = hash_api_key(token, secret=secret)

        self.assertTrue(verify_api_key(token, secret=secret, expected_hash=stored))
        self.assertFalse(verify_api_key("tok_wrong", secret=secret, expected_hash=stored))

    def test_build_api_key_storage_fields_never_contains_plaintext(self) -> None:
        token = "tok_123"
        secret = b"unit-test-secret"
        fields = build_api_key_storage_fields(token, secret=secret, label="demo")

        self.assertIn("key_hash", fields)
        self.assertIn("key_fingerprint", fields)
        self.assertNotIn(token, repr(fields))


if __name__ == "__main__":
    unittest.main()
