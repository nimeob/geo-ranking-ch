-- Async Analyze Runtime Skeleton Schema v1
-- Issue: #592 (Parent #588)
-- Stand: 2026-03-01

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'partial', 'completed', 'failed', 'canceled')),
    request_payload_hash TEXT NOT NULL,
    request_payload_ref TEXT,
    query TEXT,
    intelligence_mode TEXT,
    progress_percent INTEGER NOT NULL DEFAULT 0 CHECK (progress_percent BETWEEN 0 AND 100),
    partial_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    result_id TEXT,
    error_code TEXT,
    error_message TEXT,
    queued_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS job_events (
    event_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_seq INTEGER NOT NULL,
    occurred_at TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    payload_json TEXT,
    UNIQUE(job_id, event_seq)
);

CREATE TABLE IF NOT EXISTS job_results (
    result_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    result_kind TEXT NOT NULL CHECK (result_kind IN ('partial', 'final')),
    result_seq INTEGER NOT NULL,
    schema_version TEXT NOT NULL,
    result_payload_json TEXT NOT NULL,
    summary_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_org_status_updated
    ON jobs (org_id, status, updated_at);

CREATE INDEX IF NOT EXISTS idx_jobs_status_queued
    ON jobs (status, queued_at);

CREATE INDEX IF NOT EXISTS idx_job_events_job_occurred
    ON job_events (job_id, occurred_at);

CREATE INDEX IF NOT EXISTS idx_job_results_job_seq
    ON job_results (job_id, result_seq);
