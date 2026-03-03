#!/usr/bin/env bash
set -euo pipefail

# Prod wrapper for the remote API smoke test (sync flow: POST /analyze => HTTP 200).
#
# Usage:
#   PROD_BASE_URL="https://api.<domain>" ./scripts/run_prod_api_smoketest.sh
#   SERVICE_API_BASE_URL="https://api.<domain>" ./scripts/run_prod_api_smoketest.sh
#
# Optional auth token env vars (mapped to DEV_API_AUTH_TOKEN for the underlying script):
#   PROD_API_AUTH_TOKEN="..." ./scripts/run_prod_api_smoketest.sh
#   SERVICE_API_AUTH_TOKEN="..." ./scripts/run_prod_api_smoketest.sh
#
# Other optional knobs are forwarded (SMOKE_QUERY, SMOKE_MODE, SMOKE_TIMEOUT_SECONDS, ...).

PROD_BASE_URL_INPUT="${PROD_BASE_URL:-${SERVICE_API_BASE_URL:-}}"
PROD_API_AUTH_TOKEN_INPUT="${PROD_API_AUTH_TOKEN:-${SERVICE_API_AUTH_TOKEN:-}}"

if [[ -z "${PROD_BASE_URL_INPUT}" ]]; then
  echo "[prod-smoke] Missing PROD_BASE_URL (or SERVICE_API_BASE_URL)." >&2
  echo "[prod-smoke] Example: PROD_BASE_URL=https://api.<domain> ./scripts/run_prod_api_smoketest.sh" >&2
  exit 2
fi

export PROD_BASE_URL="${PROD_BASE_URL_INPUT}"

if [[ -n "${PROD_API_AUTH_TOKEN_INPUT}" ]]; then
  export PROD_API_AUTH_TOKEN="${PROD_API_AUTH_TOKEN_INPUT}"
fi

python3 ./scripts/run_deploy_smoke.py --profile deploy --target prod --flow sync
