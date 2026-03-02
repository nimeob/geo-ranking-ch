-- Migration: 002_async_jobs_schema
-- Description: Async analyze job history tables (jobs, job_events)
-- Issue: #803 (ASYNC-DB-0) precondition — schema definition
-- Note: These tables supersede the file-backed store (runtime/async_jobs/store.v1.json)
--       and provide persistent job history in Postgres.

BEGIN;

CREATE TABLE IF NOT EXISTS jobs (
    job_id   text PRIMARY KEY,
    org_id   text NOT NULL,
    status   text NOT NULL CHECK (status IN ('queued', 'running', 'partial', 'completed', 'failed', 'canceled')),

    request_payload_hash text NOT NULL,
    request_payload_ref  text,   -- S3 object key / URL (optional; large payloads)

    query            text,
    intelligence_mode text,

    progress_percent integer NOT NULL DEFAULT 0
        CHECK (progress_percent BETWEEN 0 AND 100),
    partial_count    integer NOT NULL DEFAULT 0,
    error_count      integer NOT NULL DEFAULT 0,

    result_id      text,
    error_code     text,
    error_message  text,

    queued_at  text NOT NULL,   -- ISO-8601 string; kept as text for wire compat
    started_at text,
    finished_at text,
    updated_at text NOT NULL
);

CREATE INDEX IF NOT EXISTS jobs_org_id_idx    ON jobs(org_id);
CREATE INDEX IF NOT EXISTS jobs_status_idx    ON jobs(status);
CREATE INDEX IF NOT EXISTS jobs_queued_at_idx ON jobs(queued_at);

CREATE TABLE IF NOT EXISTS job_events (
    event_id  text PRIMARY KEY,
    job_id    text NOT NULL,
    event_type text NOT NULL,
    event_seq  integer NOT NULL,
    occurred_at text NOT NULL
);

CREATE INDEX IF NOT EXISTS job_events_job_id_idx ON job_events(job_id);

COMMIT;
