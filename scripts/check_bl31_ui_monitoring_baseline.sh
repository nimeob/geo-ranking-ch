#!/usr/bin/env bash
set -euo pipefail

AWS_REGION="${AWS_REGION:-eu-central-1}"
ECS_CLUSTER="${ECS_CLUSTER:-swisstopo-dev}"
UI_ECS_SERVICE="${UI_ECS_SERVICE:-swisstopo-dev-ui}"
SNS_TOPIC_ARN="${SNS_TOPIC_ARN:-arn:aws:sns:eu-central-1:523234426229:swisstopo-dev-alerts}"
UI_RUNNING_TASK_ALARM="${UI_RUNNING_TASK_ALARM:-swisstopo-dev-ui-running-taskcount-low}"
UI_METRIC_NAMESPACE="${UI_METRIC_NAMESPACE:-swisstopo/dev-ui}"

UI_HEALTH_PROBE_LAMBDA="${UI_HEALTH_PROBE_LAMBDA:-swisstopo-dev-ui-health-probe}"
UI_HEALTH_PROBE_RULE="${UI_HEALTH_PROBE_RULE:-swisstopo-dev-ui-health-probe-schedule}"
UI_HEALTH_PROBE_ALARM="${UI_HEALTH_PROBE_ALARM:-swisstopo-dev-ui-health-probe-fail}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK_HEALTH_PROBE_SCRIPT="${CHECK_HEALTH_PROBE_SCRIPT:-${SCRIPT_DIR}/check_health_probe_dev.sh}"

WARNINGS=0
ERRORS=0

warn()  { echo "⚠️  WARN: $*"; WARNINGS=$((WARNINGS + 1)); }
error() { echo "❌ FAIL: $*"; ERRORS=$((ERRORS + 1)); }
ok()    { echo "✅ OK:   $*"; }

echo "== BL-31.5 UI Monitoring Baseline Check (dev, read-only) =="
echo "Region: ${AWS_REGION}"
echo "ECS:    ${ECS_CLUSTER}/${UI_ECS_SERVICE}"
echo

if ! command -v aws >/dev/null 2>&1; then
  echo "Fehler: aws CLI nicht gefunden." >&2
  exit 1
fi

if [[ ! -x "$CHECK_HEALTH_PROBE_SCRIPT" ]]; then
  echo "Fehler: Check-Script für Health-Probe fehlt oder ist nicht ausführbar: ${CHECK_HEALTH_PROBE_SCRIPT}" >&2
  exit 1
fi

if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo "Fehler: AWS Credentials nicht nutzbar (sts get-caller-identity fehlgeschlagen)." >&2
  exit 2
fi

# 1) UI ECS Service vorhanden
ui_service_arn=$(aws ecs describe-services \
  --region "$AWS_REGION" \
  --cluster "$ECS_CLUSTER" \
  --services "$UI_ECS_SERVICE" \
  --query 'services[0].serviceArn' \
  --output text 2>/dev/null || true)

if [[ "$ui_service_arn" == arn:aws:ecs:* ]]; then
  ok "UI ECS Service erreichbar"
else
  error "UI ECS Service nicht erreichbar (${ECS_CLUSTER}/${UI_ECS_SERVICE})"
fi

# 2) UI RunningTaskCount Alarm + SNS Action
ui_alarm_json=$(aws cloudwatch describe-alarms \
  --region "$AWS_REGION" \
  --alarm-names "$UI_RUNNING_TASK_ALARM" \
  --query 'MetricAlarms[0].{Name:AlarmName,Actions:AlarmActions}' \
  --output json 2>/dev/null || echo '{}')

if [[ "$ui_alarm_json" == *"${UI_RUNNING_TASK_ALARM}"* ]]; then
  ok "UI RunningTaskCount-Alarm vorhanden (${UI_RUNNING_TASK_ALARM})"

  if [[ "$ui_alarm_json" == *"${SNS_TOPIC_ARN}"* ]]; then
    ok "UI Alarm-Action zeigt auf SNS Topic"
  else
    error "UI Alarm-Action enthält SNS Topic nicht (${SNS_TOPIC_ARN})"
  fi
else
  error "UI RunningTaskCount-Alarm fehlt (${UI_RUNNING_TASK_ALARM})"
fi

# 3) Reachability-Probe (delegiert auf generischen Probe-Check)
set +e
probe_output=$(AWS_REGION="$AWS_REGION" \
  ECS_SERVICE="$UI_ECS_SERVICE" \
  METRIC_NS="$UI_METRIC_NAMESPACE" \
  LAMBDA_NAME="$UI_HEALTH_PROBE_LAMBDA" \
  RULE_NAME="$UI_HEALTH_PROBE_RULE" \
  ALARM_NAME="$UI_HEALTH_PROBE_ALARM" \
  "$CHECK_HEALTH_PROBE_SCRIPT" 2>&1)
probe_rc=$?
set -e

echo
echo "-- Reachability-Probe (${UI_HEALTH_PROBE_LAMBDA}) --"
echo "$probe_output"

if [[ $probe_rc -eq 0 ]]; then
  ok "UI Reachability-Probe operativ"
elif [[ $probe_rc -eq 10 ]]; then
  warn "UI Reachability-Probe vorhanden, aber mit Warnungen"
else
  error "UI Reachability-Probe nicht operativ (Exit ${probe_rc})"
fi

echo
if [[ $ERRORS -gt 0 ]]; then
  echo "Ergebnis: FAIL (${ERRORS} Fehler, ${WARNINGS} Warnungen)"
  exit 20
fi

if [[ $WARNINGS -gt 0 ]]; then
  echo "Ergebnis: WARN (${WARNINGS} Warnungen)"
  exit 10
fi

echo "Ergebnis: OK"
exit 0
