-- Migration: 004_entitlements_schema
-- Description: Entitlement layer tables (plans/subscriptions/entitlements/usage_counters/audit_events)
-- Reference: docs/GTM_TO_DB_ARCHITECTURE_V1.md (#811 sections: table catalog v1)
--            docs/api/entitlements-v1.md (gate catalog Free/Pro/Business)
-- Depends on: 001_core_schema.sql (organizations/users/memberships/api_keys)

BEGIN;

CREATE TABLE IF NOT EXISTS plans (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_code text NOT NULL,
  version integer NOT NULL DEFAULT 1,
  active_from timestamptz NOT NULL DEFAULT now(),
  active_to timestamptz NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT plans_code_version_unique UNIQUE (plan_code, version)
);

CREATE TABLE IF NOT EXISTS subscriptions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  plan_id uuid NOT NULL REFERENCES plans(id),
  state text NOT NULL DEFAULT 'active',
  billing_provider text NULL,
  provider_ref text NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS subscriptions_org_id_idx ON subscriptions(org_id);

-- Constraint: exactly one active subscription per org is enforced at
-- application level (GTM_TO_DB_ARCHITECTURE_V1.md tenant rule 3); history
-- remains queryable via state + created_at.
CREATE UNIQUE INDEX IF NOT EXISTS subscriptions_one_active_per_org
  ON subscriptions(org_id) WHERE state = 'active';

CREATE TABLE IF NOT EXISTS entitlements (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  subscription_id uuid NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
  key text NOT NULL,
  value jsonb NOT NULL,
  source text NOT NULL DEFAULT 'plan',
  effective_from timestamptz NOT NULL DEFAULT now(),
  effective_to timestamptz NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT entitlements_org_key_active_unique
    UNIQUE (org_id, key, effective_from)
);

CREATE INDEX IF NOT EXISTS entitlements_org_id_idx ON entitlements(org_id);
CREATE INDEX IF NOT EXISTS entitlements_org_key_idx ON entitlements(org_id, key);

CREATE TABLE IF NOT EXISTS usage_counters (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  scope_type text NOT NULL,
  scope_id text NULL,
  metric_key text NOT NULL,
  window_start timestamptz NOT NULL,
  window_end timestamptz NOT NULL,
  value bigint NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT usage_counters_scope_window_unique
    UNIQUE (org_id, scope_type, scope_id, metric_key, window_start)
);

CREATE INDEX IF NOT EXISTS usage_counters_org_window_idx
  ON usage_counters(org_id, metric_key, window_start);

CREATE TABLE IF NOT EXISTS audit_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  actor_type text NOT NULL,
  actor_id text NULL,
  action text NOT NULL,
  entity_type text NOT NULL,
  entity_id text NOT NULL,
  payload jsonb NULL,
  occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS audit_events_org_occurred_idx
  ON audit_events(org_id, occurred_at);
CREATE INDEX IF NOT EXISTS audit_events_entity_idx
  ON audit_events(entity_type, entity_id);

COMMIT;
