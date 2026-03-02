-- Async Jobs Schema v2 (canonical reference)
-- Issue: #838 (ASYNC-DB-0.wp1)
-- Stand: 2026-03-02
--
-- Applied via migrations:
--   002_async_jobs_schema.sql  — jobs + job_events
--   003_async_jobs_results.sql — job_results + user_id on jobs + S3 refs
--
-- This file documents the FULL target schema after both migrations.
-- Use db-migrate.py to apply changes; do not run this file directly.

-- -------------------------------------------------------------------------
-- jobs — one row per async analyze job
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jobs (
    job_id              text    PRIMARY KEY,
    org_id              text    NOT NULL,
    user_id             text,                       -- from migration 003 (nullable)
    status              text    NOT NULL CHECK (status IN ('queued', 'running', 'partial', 'completed', 'failed', 'canceled')),

    request_payload_hash text   NOT NULL,
    request_payload_ref  text,                      -- S3 object key / URL (optional)

    query               text,
    intelligence_mode   text,

    progress_percent    integer NOT NULL DEFAULT 0
        CHECK (progress_percent BETWEEN 0 AND 100),
    partial_count       integer NOT NULL DEFAULT 0,
    error_count         integer NOT NULL DEFAULT 0,

    result_id           text,
    error_code          text,
    error_message       text,

    queued_at           text    NOT NULL,           -- ISO-8601 string; text for wire compat
    started_at          text,
    finished_at         text,
    updated_at          text    NOT NULL
);

CREATE INDEX IF NOT EXISTS jobs_org_id_idx     ON jobs(org_id);
CREATE INDEX IF NOT EXISTS jobs_status_idx     ON jobs(status);
CREATE INDEX IF NOT EXISTS jobs_queued_at_idx  ON jobs(queued_at);
CREATE INDEX IF NOT EXISTS jobs_user_id_idx    ON jobs(user_id);
CREATE INDEX IF NOT EXISTS jobs_org_user_idx   ON jobs(org_id, user_id);

-- -------------------------------------------------------------------------
-- job_events — structured event log per job
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS job_events (
    event_id    text    PRIMARY KEY,
    job_id      text    NOT NULL,
    event_type  text    NOT NULL,
    event_seq   integer NOT NULL,
    occurred_at text    NOT NULL,
    UNIQUE(job_id, event_seq)
);

CREATE INDEX IF NOT EXISTS job_events_job_id_idx ON job_events(job_id);

-- -------------------------------------------------------------------------
-- job_results — persistent result store for async analyze outcomes
--
-- Large result payloads are stored in S3; this table keeps metadata and a
-- compact summary_json inline.  Small payloads may omit s3_key (NULL).
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS job_results (
    result_id       text    PRIMARY KEY,
    job_id          text    NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    org_id          text    NOT NULL,
    user_id         text,                           -- nullable until OIDC mapping done
    result_kind     text    NOT NULL CHECK (result_kind IN ('partial', 'final')),
    result_seq      integer NOT NULL,
    schema_version  text    NOT NULL,

    -- S3 payload reference (NULL when payload is fully inline)
    s3_bucket       text,
    s3_key          text,
    checksum_sha256 text,
    content_type    text    NOT NULL DEFAULT 'application/json',
    size_bytes      bigint,

    -- Compact inline summary (always present; full payload optionally in S3)
    summary_json    text,

    created_at      text    NOT NULL,               -- ISO-8601 string

    CONSTRAINT job_results_job_seq_unique UNIQUE (job_id, result_seq)
);

CREATE INDEX IF NOT EXISTS job_results_org_id_idx     ON job_results(org_id);
CREATE INDEX IF NOT EXISTS job_results_job_id_idx     ON job_results(job_id);
CREATE INDEX IF NOT EXISTS job_results_user_id_idx    ON job_results(user_id);
CREATE INDEX IF NOT EXISTS job_results_created_at_idx ON job_results(created_at);
