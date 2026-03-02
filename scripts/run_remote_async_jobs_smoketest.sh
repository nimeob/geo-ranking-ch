#!/usr/bin/env bash
set -euo pipefail

# Reproducible Remote Smoke Test (Async Jobs API)
#
# Purpose:
# - Submit an async analyze job, poll job status until completion, then fetch the result.
# - Works for dev/staging/prod (base URL via env vars).
# - Produces a clear PASS/FAIL and (optionally) a structured JSON evidence file.
#
# Usage:
#   # Minimal (no auth)
#   DEV_BASE_URL="https://api.<domain>" ./scripts/run_remote_async_jobs_smoketest.sh
#
#   # With optional auth token
#   DEV_BASE_URL="https://api.<domain>" DEV_API_AUTH_TOKEN="<token>" ./scripts/run_remote_async_jobs_smoketest.sh
#
# Alternative env var names (supported):
#   SERVICE_API_BASE_URL, SERVICE_API_AUTH_TOKEN
#
# Optional knobs forwarded to the Python runner:
#   SMOKE_QUERY, SMOKE_MODE, SMOKE_TIMEOUT_SECONDS,
#   ASYNC_SMOKE_POLL_TIMEOUT_SECONDS, ASYNC_SMOKE_POLL_INTERVAL_SECONDS,
#   ASYNC_SMOKE_OUTPUT_JSON,
#   TLS_CA_CERT / DEV_TLS_CA_CERT

REMOTE_BASE_URL_INPUT="${DEV_BASE_URL:-${SERVICE_API_BASE_URL:-}}"
REMOTE_API_AUTH_TOKEN_INPUT="${DEV_API_AUTH_TOKEN:-${SERVICE_API_AUTH_TOKEN:-}}"

if [[ -z "${REMOTE_BASE_URL_INPUT}" ]]; then
  echo "[remote-async-smoke] Missing DEV_BASE_URL (or SERVICE_API_BASE_URL)." >&2
  echo "[remote-async-smoke] Example: DEV_BASE_URL=https://api.<domain> ./scripts/run_remote_async_jobs_smoketest.sh" >&2
  exit 2
fi

# Default evidence artefact path (may be overridden by ASYNC_SMOKE_OUTPUT_JSON).
if [[ -z "${ASYNC_SMOKE_OUTPUT_JSON:-}" ]]; then
  export ASYNC_SMOKE_OUTPUT_JSON="artifacts/remote-smoke-async-jobs.json"
fi

export SERVICE_API_BASE_URL="${REMOTE_BASE_URL_INPUT}"

if [[ -n "${REMOTE_API_AUTH_TOKEN_INPUT}" ]]; then
  export SERVICE_API_AUTH_TOKEN="${REMOTE_API_AUTH_TOKEN_INPUT}"
fi

python3 scripts/run_async_jobs_smoketest.py
