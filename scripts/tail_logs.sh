#!/usr/bin/env bash
set -euo pipefail

AWS_REGION="${AWS_REGION:-eu-central-1}"
LOG_GROUP="${LOG_GROUP:-/swisstopo/dev/ecs/api}"
SINCE="${SINCE:-30m}"
FOLLOW=1

usage() {
  cat <<'USAGE'
Usage: tail_logs.sh [--since <duration>] [--no-follow] [--log-group <name>] [--region <aws-region>]

Defaults:
  --since      30m
  --log-group  /swisstopo/dev/ecs/api
  --region     eu-central-1
  follow       enabled

Examples:
  ./scripts/tail_logs.sh
  ./scripts/tail_logs.sh --since 2h
  ./scripts/tail_logs.sh --no-follow --log-group /aws/ecs/custom-service
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --since)
      SINCE="$2"
      shift 2
      ;;
    --no-follow)
      FOLLOW=0
      shift
      ;;
    --log-group)
      LOG_GROUP="$2"
      shift 2
      ;;
    --region)
      AWS_REGION="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unbekanntes Argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if ! command -v aws >/dev/null 2>&1; then
  echo "Fehler: aws CLI nicht gefunden." >&2
  exit 1
fi

echo "Tailing logs from ${LOG_GROUP} (region=${AWS_REGION}, since=${SINCE}, follow=${FOLLOW})"

if [[ "${FOLLOW}" -eq 1 ]]; then
  aws logs tail "${LOG_GROUP}" --region "${AWS_REGION}" --since "${SINCE}" --follow
else
  aws logs tail "${LOG_GROUP}" --region "${AWS_REGION}" --since "${SINCE}"
fi
