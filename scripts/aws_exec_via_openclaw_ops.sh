#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <aws-subcommand...>" >&2
  echo "Example: $0 ecs list-clusters --region eu-central-1" >&2
  exit 2
fi

ROLE_ARN="${OPENCLAW_OPS_ROLE_ARN:-arn:aws:iam::523234426229:role/openclaw-ops-role}"
SESSION_NAME="openclaw-ops-exec-$(date +%s)"
DURATION_SECONDS="${OPENCLAW_OPS_SESSION_SECONDS:-3600}"

ASSUME_JSON=$(aws sts assume-role \
  --role-arn "$ROLE_ARN" \
  --role-session-name "$SESSION_NAME" \
  --duration-seconds "$DURATION_SECONDS")

export AWS_ACCESS_KEY_ID=$(echo "$ASSUME_JSON" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["Credentials"]["AccessKeyId"])')
export AWS_SECRET_ACCESS_KEY=$(echo "$ASSUME_JSON" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["Credentials"]["SecretAccessKey"])')
export AWS_SESSION_TOKEN=$(echo "$ASSUME_JSON" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["Credentials"]["SessionToken"])')

aws "$@"
