#!/usr/bin/env bash
set -euo pipefail

AWS_REGION="${AWS_REGION:-eu-central-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-523234426229}"
ECS_CLUSTER="${ECS_CLUSTER:-swisstopo-dev}"
UI_ECS_SERVICE="${UI_ECS_SERVICE:-swisstopo-dev-ui}"
SNS_TOPIC_ARN="${SNS_TOPIC_ARN:-arn:aws:sns:eu-central-1:523234426229:swisstopo-dev-alerts}"

UI_RUNNING_TASK_ALARM="${UI_RUNNING_TASK_ALARM:-swisstopo-dev-ui-running-taskcount-low}"
UI_METRIC_NAMESPACE="${UI_METRIC_NAMESPACE:-swisstopo/dev-ui}"
UI_HEALTH_PATH="${UI_HEALTH_PATH:-/healthz}"
UI_HEALTH_PORT="${UI_HEALTH_PORT:-8080}"

UI_HEALTH_PROBE_LAMBDA="${UI_HEALTH_PROBE_LAMBDA:-swisstopo-dev-ui-health-probe}"
UI_HEALTH_PROBE_ROLE="${UI_HEALTH_PROBE_ROLE:-swisstopo-dev-ui-health-probe-role}"
UI_HEALTH_PROBE_RULE="${UI_HEALTH_PROBE_RULE:-swisstopo-dev-ui-health-probe-schedule}"
UI_HEALTH_PROBE_ALARM="${UI_HEALTH_PROBE_ALARM:-swisstopo-dev-ui-health-probe-fail}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_HEALTH_PROBE_SCRIPT="${SETUP_HEALTH_PROBE_SCRIPT:-${SCRIPT_DIR}/setup_health_probe_dev.sh}"

if ! command -v aws >/dev/null 2>&1; then
  echo "Fehler: aws CLI nicht gefunden." >&2
  exit 1
fi

if [[ ! -x "$SETUP_HEALTH_PROBE_SCRIPT" ]]; then
  echo "Fehler: Setup-Script für Health-Probe fehlt oder ist nicht ausführbar: ${SETUP_HEALTH_PROBE_SCRIPT}" >&2
  exit 1
fi

if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo "Fehler: AWS Credentials nicht nutzbar (sts get-caller-identity fehlgeschlagen)." >&2
  exit 2
fi

if ! aws ecs describe-services \
  --region "$AWS_REGION" \
  --cluster "$ECS_CLUSTER" \
  --services "$UI_ECS_SERVICE" \
  --query 'services[0].serviceArn' \
  --output text | grep -q '^arn:aws:ecs:'; then
  echo "Fehler: UI ECS Service nicht erreichbar (${ECS_CLUSTER}/${UI_ECS_SERVICE})." >&2
  exit 3
fi

echo "== BL-31.5 UI Monitoring Baseline Setup (dev) =="
echo "Region:      ${AWS_REGION}"
echo "ECS:         ${ECS_CLUSTER}/${UI_ECS_SERVICE}"
echo "SNS Topic:   ${SNS_TOPIC_ARN}"
echo "UI Alarm:    ${UI_RUNNING_TASK_ALARM}"
echo

echo "[1/2] Alarm: UI-Service-Ausfall (RunningTaskCount < 1) ..."
aws cloudwatch put-metric-alarm \
  --region "$AWS_REGION" \
  --alarm-name "$UI_RUNNING_TASK_ALARM" \
  --alarm-description "UI service unhealthy: running tasks < 1" \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --ok-actions "$SNS_TOPIC_ARN" \
  --namespace AWS/ECS \
  --metric-name RunningTaskCount \
  --dimensions Name=ClusterName,Value="$ECS_CLUSTER" Name=ServiceName,Value="$UI_ECS_SERVICE" \
  --statistic Minimum \
  --period 60 \
  --evaluation-periods 3 \
  --datapoints-to-alarm 3 \
  --threshold 1 \
  --comparison-operator LessThanThreshold \
  --treat-missing-data breaching

echo

echo "[2/2] Reachability-Probe (/healthz) für UI-Service bereitstellen ..."
AWS_REGION="$AWS_REGION" \
AWS_ACCOUNT_ID="$AWS_ACCOUNT_ID" \
ECS_CLUSTER="$ECS_CLUSTER" \
ECS_SERVICE="$UI_ECS_SERVICE" \
HEALTH_PORT="$UI_HEALTH_PORT" \
HEALTH_PATH="$UI_HEALTH_PATH" \
METRIC_NS="$UI_METRIC_NAMESPACE" \
SNS_TOPIC_ARN="$SNS_TOPIC_ARN" \
LAMBDA_NAME="$UI_HEALTH_PROBE_LAMBDA" \
ROLE_NAME="$UI_HEALTH_PROBE_ROLE" \
RULE_NAME="$UI_HEALTH_PROBE_RULE" \
ALARM_NAME="$UI_HEALTH_PROBE_ALARM" \
"$SETUP_HEALTH_PROBE_SCRIPT"

echo
echo "Setup abgeschlossen."
echo "- RunningTaskCount-Alarm: ${UI_RUNNING_TASK_ALARM}"
echo "- Reachability-Alarm:    ${UI_HEALTH_PROBE_ALARM}"
echo "- Probe-Lambda:          ${UI_HEALTH_PROBE_LAMBDA}"
