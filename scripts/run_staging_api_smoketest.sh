#!/usr/bin/env bash
set -euo pipefail

# Staging wrapper for the remote API smoke test (POST /analyze => 200).
#
# Motivation:
# - Make the staging smoke reproducible with a single, environment-named entrypoint.
# - Reuse the hardened curl/json validation in ./scripts/run_remote_api_smoketest.sh.
#
# Usage:
#   STAGING_BASE_URL="https://api.staging.<domain>" ./scripts/run_staging_api_smoketest.sh
#   SERVICE_API_BASE_URL="https://api.staging.<domain>" ./scripts/run_staging_api_smoketest.sh
#
# Optional auth token env vars (mapped to DEV_API_AUTH_TOKEN for the underlying script):
#   STAGING_API_AUTH_TOKEN="..." ./scripts/run_staging_api_smoketest.sh
#   SERVICE_API_AUTH_TOKEN="..." ./scripts/run_staging_api_smoketest.sh
#
# Other optional knobs are forwarded (SMOKE_QUERY, SMOKE_MODE, SMOKE_TIMEOUT_SECONDS, ...).

STAGING_BASE_URL_INPUT="${STAGING_BASE_URL:-${SERVICE_API_BASE_URL:-}}"
STAGING_API_AUTH_TOKEN_INPUT="${STAGING_API_AUTH_TOKEN:-${SERVICE_API_AUTH_TOKEN:-}}"

if [[ -z "${STAGING_BASE_URL_INPUT}" ]]; then
  echo "[staging-smoke] Missing STAGING_BASE_URL (or SERVICE_API_BASE_URL)." >&2
  echo "[staging-smoke] Example: STAGING_BASE_URL=https://api.staging.<domain> ./scripts/run_staging_api_smoketest.sh" >&2
  exit 2
fi

# Default evidence artefact path (may be overridden by SMOKE_OUTPUT_JSON).
if [[ -z "${SMOKE_OUTPUT_JSON:-}" ]]; then
  export SMOKE_OUTPUT_JSON="artifacts/staging-smoke-analyze.json"
fi

export DEV_BASE_URL="${STAGING_BASE_URL_INPUT}"

if [[ -n "${STAGING_API_AUTH_TOKEN_INPUT}" ]]; then
  export DEV_API_AUTH_TOKEN="${STAGING_API_AUTH_TOKEN_INPUT}"
fi

./scripts/run_remote_api_smoketest.sh
