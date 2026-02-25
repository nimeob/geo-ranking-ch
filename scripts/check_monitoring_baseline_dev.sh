#!/usr/bin/env bash
set -euo pipefail

AWS_REGION="${AWS_REGION:-eu-central-1}"
ECS_CLUSTER="${ECS_CLUSTER:-swisstopo-dev}"
ECS_SERVICE="${ECS_SERVICE:-swisstopo-dev-api}"
LOG_GROUP="${LOG_GROUP:-/swisstopo/dev/ecs/api}"
SNS_TOPIC_ARN="${SNS_TOPIC_ARN:-arn:aws:sns:eu-central-1:523234426229:swisstopo-dev-alerts}"
METRIC_NAMESPACE="${METRIC_NAMESPACE:-swisstopo/dev-api}"

ALARM_TASK_LOW="swisstopo-dev-api-running-taskcount-low"
ALARM_5XX_RATE="swisstopo-dev-api-http-5xx-rate-high"
FILTER_HTTP_TOTAL="swisstopo-dev-api-http-total"
FILTER_HTTP_5XX="swisstopo-dev-api-http-5xx"

if ! command -v aws >/dev/null 2>&1; then
  echo "Fehler: aws CLI nicht gefunden." >&2
  exit 1
fi

if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo "Fehler: AWS Credentials nicht nutzbar (sts get-caller-identity fehlgeschlagen)." >&2
  exit 2
fi

status_ok=true
warn_count=0

pass() {
  echo "✅ $1"
}

warn() {
  echo "⚠️  $1"
  warn_count=$((warn_count + 1))
}

fail() {
  echo "❌ $1"
  status_ok=false
}

echo "== Monitoring Baseline Check (dev, read-only) =="
echo "Region:    ${AWS_REGION}"
echo "ECS:       ${ECS_CLUSTER}/${ECS_SERVICE}"
echo "Log Group: ${LOG_GROUP}"
echo "SNS Topic: ${SNS_TOPIC_ARN}"
echo

# 1) ECS service reachable
if aws ecs describe-services \
  --region "$AWS_REGION" \
  --cluster "$ECS_CLUSTER" \
  --services "$ECS_SERVICE" \
  --query 'services[0].serviceArn' \
  --output text | grep -q '^arn:aws:ecs:'; then
  pass "ECS Service erreichbar"
else
  fail "ECS Service nicht erreichbar (${ECS_CLUSTER}/${ECS_SERVICE})"
fi

# 2) Log group exists + retention
log_group_name=$(aws logs describe-log-groups \
  --region "$AWS_REGION" \
  --log-group-name-prefix "$LOG_GROUP" \
  --query "logGroups[?logGroupName=='${LOG_GROUP}'] | [0].logGroupName" \
  --output text)

if [[ "$log_group_name" == "$LOG_GROUP" ]]; then
  retention_days=$(aws logs describe-log-groups \
    --region "$AWS_REGION" \
    --log-group-name-prefix "$LOG_GROUP" \
    --query "logGroups[?logGroupName=='${LOG_GROUP}'] | [0].retentionInDays" \
    --output text)

  if [[ "$retention_days" == "30" ]]; then
    pass "CloudWatch Log Group vorhanden (Retention: 30 Tage)"
  elif [[ "$retention_days" == "None" || -z "$retention_days" ]]; then
    warn "CloudWatch Log Group vorhanden, aber ohne gesetzte Retention"
  else
    warn "CloudWatch Log Group vorhanden, Retention=${retention_days} (erwartet: 30)"
  fi
else
  fail "CloudWatch Log Group fehlt (${LOG_GROUP})"
fi

# 3) Metric filters
metric_filters=$(aws logs describe-metric-filters \
  --region "$AWS_REGION" \
  --log-group-name "$LOG_GROUP" \
  --query "metricFilters[?filterName=='${FILTER_HTTP_TOTAL}' || filterName=='${FILTER_HTTP_5XX}'].filterName" \
  --output text)

if [[ "$metric_filters" == *"${FILTER_HTTP_TOTAL}"* && "$metric_filters" == *"${FILTER_HTTP_5XX}"* ]]; then
  pass "Metric Filters vorhanden (${FILTER_HTTP_TOTAL}, ${FILTER_HTTP_5XX})"
else
  fail "Metric Filters unvollständig (erwartet: ${FILTER_HTTP_TOTAL}, ${FILTER_HTTP_5XX})"
fi

# 4) Alarms + actions
alarm_descriptions=$(aws cloudwatch describe-alarms \
  --region "$AWS_REGION" \
  --alarm-names "$ALARM_TASK_LOW" "$ALARM_5XX_RATE" \
  --query 'MetricAlarms[].{Name:AlarmName,Actions:AlarmActions}' \
  --output json)

if [[ "$alarm_descriptions" == *"${ALARM_TASK_LOW}"* && "$alarm_descriptions" == *"${ALARM_5XX_RATE}"* ]]; then
  pass "CloudWatch Alarme vorhanden (${ALARM_TASK_LOW}, ${ALARM_5XX_RATE})"

  if [[ "$alarm_descriptions" == *"${SNS_TOPIC_ARN}"* ]]; then
    pass "Alarm-Actions zeigen auf SNS Topic"
  else
    fail "Alarm-Actions enthalten SNS Topic nicht (${SNS_TOPIC_ARN})"
  fi
else
  fail "Mindestens ein CloudWatch Alarm fehlt (${ALARM_TASK_LOW}/${ALARM_5XX_RATE})"
fi

# 5) SNS topic + subscriber status
sns_topic_exists=$(aws sns get-topic-attributes \
  --region "$AWS_REGION" \
  --topic-arn "$SNS_TOPIC_ARN" \
  --query 'Attributes.TopicArn' \
  --output text 2>/dev/null || true)

if [[ "$sns_topic_exists" == "$SNS_TOPIC_ARN" ]]; then
  pass "SNS Topic vorhanden"

  subscriber_stats=$(aws sns list-subscriptions-by-topic \
    --region "$AWS_REGION" \
    --topic-arn "$SNS_TOPIC_ARN" \
    --query '{confirmed:length(Subscriptions[?SubscriptionArn!=`PendingConfirmation`]),pending:length(Subscriptions[?SubscriptionArn==`PendingConfirmation`])}' \
    --output json)

  confirmed_count=$(echo "$subscriber_stats" | python3 -c 'import json,sys; print(json.load(sys.stdin)["confirmed"])')
  pending_count=$(echo "$subscriber_stats" | python3 -c 'import json,sys; print(json.load(sys.stdin)["pending"])')

  if (( confirmed_count > 0 )); then
    pass "SNS Subscriber bestätigt (${confirmed_count} bestätigt, ${pending_count} pending)"
  elif (( pending_count > 0 )); then
    warn "Keine bestätigten Subscriber (${pending_count} pending)"
  else
    warn "Keine SNS Subscriber vorhanden"
  fi
else
  fail "SNS Topic nicht gefunden (${SNS_TOPIC_ARN})"
fi

echo
if [[ "$status_ok" == true ]]; then
  if (( warn_count > 0 )); then
    echo "Ergebnis: WARN (${warn_count} Hinweis(e))"
    exit 10
  fi
  echo "Ergebnis: OK"
  exit 0
fi

echo "Ergebnis: FAIL"
exit 20
