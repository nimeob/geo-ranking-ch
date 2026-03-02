-- Migration: 003_async_jobs_results
-- Description: Async job results table + user_id on jobs + S3 payload reference fields
-- Issue: #838 (ASYNC-DB-0.wp1)
-- Depends on: 002_async_jobs_schema

BEGIN;

-- -------------------------------------------------------------------------
-- Add user_id to jobs (nullable; populated once OIDC user mapping is done)
-- -------------------------------------------------------------------------
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS user_id text;

CREATE INDEX IF NOT EXISTS jobs_user_id_idx ON jobs(user_id);
CREATE INDEX IF NOT EXISTS jobs_org_user_idx ON jobs(org_id, user_id);

-- -------------------------------------------------------------------------
-- job_results — persistent result store for async analyze outcomes
--
-- Large result payloads are stored in S3; this table keeps the metadata and
-- a compact summary_json inline.  Small payloads (<= S3 threshold) may be
-- stored inline in summary_json; s3_key will be NULL in that case.
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS job_results (
    result_id       text        PRIMARY KEY,
    job_id          text        NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    org_id          text        NOT NULL,
    user_id         text,                           -- nullable until OIDC mapping done
    result_kind     text        NOT NULL CHECK (result_kind IN ('partial', 'final')),
    result_seq      integer     NOT NULL,
    schema_version  text        NOT NULL,

    -- S3 payload reference (NULL when payload is fully inline)
    s3_bucket       text,
    s3_key          text,
    checksum_sha256 text,
    content_type    text        NOT NULL DEFAULT 'application/json',
    size_bytes      bigint,

    -- Compact inline summary (always present; full payload optionally in S3)
    summary_json    text,

    created_at      text        NOT NULL,           -- ISO-8601 string for wire compat

    CONSTRAINT job_results_job_seq_unique UNIQUE (job_id, result_seq)
);

CREATE INDEX IF NOT EXISTS job_results_org_id_idx    ON job_results(org_id);
CREATE INDEX IF NOT EXISTS job_results_job_id_idx    ON job_results(job_id);
CREATE INDEX IF NOT EXISTS job_results_user_id_idx   ON job_results(user_id);
CREATE INDEX IF NOT EXISTS job_results_created_at_idx ON job_results(created_at);

COMMIT;
