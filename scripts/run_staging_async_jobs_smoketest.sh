#!/usr/bin/env bash
set -euo pipefail

# Staging wrapper for the Async Jobs API smoke test (submit/status/result).
#
# Usage:
#   STAGING_BASE_URL="https://api.staging.<domain>" ./scripts/run_staging_async_jobs_smoketest.sh
#   SERVICE_API_BASE_URL="https://api.staging.<domain>" ./scripts/run_staging_async_jobs_smoketest.sh
#
# Optional auth token env vars (mapped to SERVICE_API_AUTH_TOKEN):
#   STAGING_API_AUTH_TOKEN="..." ./scripts/run_staging_async_jobs_smoketest.sh
#   SERVICE_API_AUTH_TOKEN="..." ./scripts/run_staging_async_jobs_smoketest.sh
#
# Optional knobs:
#   SMOKE_QUERY, SMOKE_MODE, SMOKE_TIMEOUT_SECONDS,
#   ASYNC_SMOKE_POLL_TIMEOUT_SECONDS, ASYNC_SMOKE_POLL_INTERVAL_SECONDS,
#   ASYNC_SMOKE_OUTPUT_JSON

STAGING_BASE_URL_INPUT="${STAGING_BASE_URL:-${SERVICE_API_BASE_URL:-}}"
STAGING_API_AUTH_TOKEN_INPUT="${STAGING_API_AUTH_TOKEN:-${SERVICE_API_AUTH_TOKEN:-}}"

if [[ -z "${STAGING_BASE_URL_INPUT}" ]]; then
  echo "[staging-async-smoke] Missing STAGING_BASE_URL (or SERVICE_API_BASE_URL)." >&2
  echo "[staging-async-smoke] Example: STAGING_BASE_URL=https://api.staging.<domain> ./scripts/run_staging_async_jobs_smoketest.sh" >&2
  exit 2
fi

# Default evidence artefact path (may be overridden by ASYNC_SMOKE_OUTPUT_JSON).
if [[ -z "${ASYNC_SMOKE_OUTPUT_JSON:-}" ]]; then
  export ASYNC_SMOKE_OUTPUT_JSON="artifacts/staging-smoke-async-jobs.json"
fi

export SERVICE_API_BASE_URL="${STAGING_BASE_URL_INPUT}"

if [[ -n "${STAGING_API_AUTH_TOKEN_INPUT}" ]]; then
  export SERVICE_API_AUTH_TOKEN="${STAGING_API_AUTH_TOKEN_INPUT}"
fi

python3 scripts/run_async_jobs_smoketest.py
