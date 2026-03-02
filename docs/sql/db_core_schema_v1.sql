-- db_core_schema_v1.sql
-- Canonical DB schema (v1) for multi-tenant identity + API key artifacts.
-- Target: Postgres 15+ (AWS RDS).
--
-- Notes:
-- - IDs are UUIDs; requires pgcrypto for gen_random_uuid() default.
-- - api_keys stores ONLY hash/fingerprint metadata (never plaintext tokens).

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS organizations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL,
  display_name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT organizations_slug_unique UNIQUE (slug)
);

CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

  -- OIDC subject ("sub") or other stable external identity.
  external_subject text NOT NULL,

  email text NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT users_external_subject_unique UNIQUE (external_subject)
);

CREATE TABLE IF NOT EXISTS memberships (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  -- Examples: owner|admin|member|viewer
  role text NOT NULL,

  created_at timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT memberships_org_user_unique UNIQUE (org_id, user_id)
);

CREATE INDEX IF NOT EXISTS memberships_org_id_idx ON memberships(org_id);
CREATE INDEX IF NOT EXISTS memberships_user_id_idx ON memberships(user_id);

CREATE TABLE IF NOT EXISTS api_keys (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

  -- Optional: user that created/owns the key.
  created_by_user_id uuid NULL REFERENCES users(id) ON DELETE SET NULL,

  label text NULL,

  -- Lookup key: short stable fingerprint (e.g. first 12 hex chars of SHA-256).
  key_fingerprint text NOT NULL,

  -- Full secret material is NEVER stored. Hash should be produced with a strong, versioned scheme.
  -- Example scheme: hmac_sha256_v1, argon2id_v1, bcrypt_v1.
  key_hash text NOT NULL,
  hash_scheme text NOT NULL DEFAULT 'hmac_sha256_v1',

  created_at timestamptz NOT NULL DEFAULT now(),
  revoked_at timestamptz NULL,
  last_used_at timestamptz NULL,

  CONSTRAINT api_keys_org_fingerprint_unique UNIQUE (org_id, key_fingerprint)
);

CREATE INDEX IF NOT EXISTS api_keys_org_id_idx ON api_keys(org_id);
CREATE INDEX IF NOT EXISTS api_keys_last_used_at_idx ON api_keys(last_used_at);

COMMIT;
