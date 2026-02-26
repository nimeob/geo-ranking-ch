#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: ./scripts/openclaw_runtime_assumerole_exec.sh <command...>
Example:
  ./scripts/openclaw_runtime_assumerole_exec.sh openclaw gateway status

Purpose:
  Starts a command in an AssumeRole-first runtime context.
  Long-lived AWS env keys are replaced by temporary STS session credentials.

Optional env vars:
  OPENCLAW_OPS_ROLE_ARN          (default: arn:aws:iam::523234426229:role/openclaw-ops-role)
  OPENCLAW_OPS_SESSION_SECONDS   (default: 3600, range: 900..43200)
  OPENCLAW_OPS_SESSION_NAME      (default: openclaw-runtime-<epoch>)
USAGE
}

die() {
  local msg="${1:-unexpected error}"
  local code="${2:-2}"
  printf 'ERROR: %s\n' "$msg" >&2
  exit "$code"
}

if [[ "$#" -lt 1 ]]; then
  usage
  exit 2
fi

if ! command -v aws >/dev/null 2>&1; then
  die "aws CLI not found in PATH" 20
fi
if ! command -v python3 >/dev/null 2>&1; then
  die "python3 not found in PATH" 20
fi

ROLE_ARN="${OPENCLAW_OPS_ROLE_ARN:-arn:aws:iam::523234426229:role/openclaw-ops-role}"
if [[ ! "$ROLE_ARN" =~ ^arn:aws:iam::[0-9]{12}:role/.+ ]]; then
  die "OPENCLAW_OPS_ROLE_ARN must match arn:aws:iam::<account-id>:role/<name>" 2
fi

SESSION_SECONDS_RAW="${OPENCLAW_OPS_SESSION_SECONDS:-3600}"
if [[ ! "$SESSION_SECONDS_RAW" =~ ^[0-9]+$ ]]; then
  die "OPENCLAW_OPS_SESSION_SECONDS must be an integer between 900 and 43200" 2
fi
SESSION_SECONDS="$SESSION_SECONDS_RAW"
if (( SESSION_SECONDS < 900 || SESSION_SECONDS > 43200 )); then
  die "OPENCLAW_OPS_SESSION_SECONDS must be between 900 and 43200" 2
fi

SESSION_NAME="${OPENCLAW_OPS_SESSION_NAME:-openclaw-runtime-$(date +%s)}"
if [[ -z "$SESSION_NAME" ]]; then
  die "OPENCLAW_OPS_SESSION_NAME must not be empty" 2
fi
if (( ${#SESSION_NAME} > 64 )); then
  die "OPENCLAW_OPS_SESSION_NAME must be <= 64 chars" 2
fi
if [[ ! "$SESSION_NAME" =~ ^[A-Za-z0-9+=,.@_-]+$ ]]; then
  die "OPENCLAW_OPS_SESSION_NAME contains invalid characters" 2
fi

ASSUME_OUTPUT=""
if ! ASSUME_OUTPUT=$(aws sts assume-role \
  --role-arn "$ROLE_ARN" \
  --role-session-name "$SESSION_NAME" \
  --duration-seconds "$SESSION_SECONDS" 2>&1); then
  die "aws sts assume-role failed: $ASSUME_OUTPUT" 30
fi

CREDENTIALS=""
if ! CREDENTIALS=$(printf '%s' "$ASSUME_OUTPUT" | python3 -c '
import json
import sys

try:
    payload = json.load(sys.stdin)
except Exception as exc:
    raise SystemExit(f"json-parse-error:{exc}")

creds = payload.get("Credentials") or {}
values = [
    creds.get("AccessKeyId", ""),
    creds.get("SecretAccessKey", ""),
    creds.get("SessionToken", ""),
]
if not all(values):
    raise SystemExit("missing-credentials")

print("\t".join(values))
'); then
  die "Failed to parse assume-role credentials JSON" 30
fi

IFS=$'\t' read -r ASSUMED_ACCESS_KEY ASSUMED_SECRET_KEY ASSUMED_SESSION_TOKEN <<<"$CREDENTIALS"
if [[ -z "$ASSUMED_ACCESS_KEY" || -z "$ASSUMED_SECRET_KEY" || -z "$ASSUMED_SESSION_TOKEN" ]]; then
  die "Assume-role response missing credential fields" 30
fi

export AWS_ACCESS_KEY_ID="$ASSUMED_ACCESS_KEY"
export AWS_SECRET_ACCESS_KEY="$ASSUMED_SECRET_KEY"
export AWS_SESSION_TOKEN="$ASSUMED_SESSION_TOKEN"
unset AWS_SECURITY_TOKEN
unset AWS_PROFILE
unset AWS_DEFAULT_PROFILE
export OPENCLAW_ASSUME_ROLE_FIRST=1

exec "$@"
