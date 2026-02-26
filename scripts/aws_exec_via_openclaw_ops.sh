#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: ./scripts/aws_exec_via_openclaw_ops.sh <aws-subcommand...>
Example: ./scripts/aws_exec_via_openclaw_ops.sh ecs list-clusters --region eu-central-1

Optional env vars:
  OPENCLAW_OPS_ROLE_ARN          (default: arn:aws:iam::523234426229:role/openclaw-ops-role)
  OPENCLAW_OPS_SESSION_SECONDS   (default: 3600, allowed: 900..43200)
  OPENCLAW_OPS_SESSION_NAME      (default: openclaw-ops-exec-<epoch>)
EOF
}

die() {
  local message="${1:-unexpected error}"
  local code="${2:-2}"
  printf 'ERROR: %s\n' "$message" >&2
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

DURATION_SECONDS_RAW="${OPENCLAW_OPS_SESSION_SECONDS:-3600}"
if [[ ! "$DURATION_SECONDS_RAW" =~ ^[0-9]+$ ]]; then
  die "OPENCLAW_OPS_SESSION_SECONDS must be an integer between 900 and 43200" 2
fi
DURATION_SECONDS="$DURATION_SECONDS_RAW"
if (( DURATION_SECONDS < 900 || DURATION_SECONDS > 43200 )); then
  die "OPENCLAW_OPS_SESSION_SECONDS must be between 900 and 43200" 2
fi

SESSION_NAME="${OPENCLAW_OPS_SESSION_NAME:-openclaw-ops-exec-$(date +%s)}"
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
  --duration-seconds "$DURATION_SECONDS" 2>&1); then
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

IFS=$'\t' read -r AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN <<<"$CREDENTIALS"
if [[ -z "$AWS_ACCESS_KEY_ID" || -z "$AWS_SECRET_ACCESS_KEY" || -z "$AWS_SESSION_TOKEN" ]]; then
  die "Assume-role response missing credential fields" 30
fi

export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
exec aws "$@"
