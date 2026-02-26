#!/usr/bin/env bash
set -euo pipefail
ROLE_ARN="${1:-arn:aws:iam::523234426229:role/openclaw-ops-role}"
SESSION_NAME="${2:-openclaw-ops-$(date +%s)}"
DURATION="${3:-3600}"

ASSUME_JSON=$(aws sts assume-role \
  --role-arn "$ROLE_ARN" \
  --role-session-name "$SESSION_NAME" \
  --duration-seconds "$DURATION")

export AWS_ACCESS_KEY_ID=$(echo "$ASSUME_JSON" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["Credentials"]["AccessKeyId"])')
export AWS_SECRET_ACCESS_KEY=$(echo "$ASSUME_JSON" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["Credentials"]["SecretAccessKey"])')
export AWS_SESSION_TOKEN=$(echo "$ASSUME_JSON" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["Credentials"]["SessionToken"])')

echo "Assumed role: $ROLE_ARN"
aws sts get-caller-identity --query Arn --output text
