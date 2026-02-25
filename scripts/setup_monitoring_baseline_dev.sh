#!/usr/bin/env bash
set -euo pipefail

AWS_REGION="${AWS_REGION:-eu-central-1}"
ECS_CLUSTER="${ECS_CLUSTER:-swisstopo-dev}"
ECS_SERVICE="${ECS_SERVICE:-swisstopo-dev-api}"
LOG_GROUP="${LOG_GROUP:-/swisstopo/dev/ecs/api}"
SNS_TOPIC_NAME="${SNS_TOPIC_NAME:-swisstopo-dev-alerts}"
METRIC_NAMESPACE="${METRIC_NAMESPACE:-swisstopo/dev-api}"
ALERT_EMAIL="${ALERT_EMAIL:-}"

if ! command -v aws >/dev/null 2>&1; then
  echo "Fehler: aws CLI nicht gefunden." >&2
  exit 1
fi

if ! aws ecs describe-services \
  --region "$AWS_REGION" \
  --cluster "$ECS_CLUSTER" \
  --services "$ECS_SERVICE" \
  --query 'services[0].serviceArn' \
  --output text >/dev/null; then
  echo "Fehler: ECS Service nicht erreichbar (${ECS_CLUSTER}/${ECS_SERVICE})." >&2
  exit 2
fi

if ! aws logs describe-log-groups \
  --region "$AWS_REGION" \
  --log-group-name-prefix "$LOG_GROUP" \
  --query "logGroups[?logGroupName=='${LOG_GROUP}'] | [0].logGroupName" \
  --output text | grep -q "$LOG_GROUP"; then
  echo "Fehler: Log Group nicht gefunden (${LOG_GROUP})." >&2
  exit 3
fi

echo "== Monitoring Baseline (dev) =="
echo "Region:      ${AWS_REGION}"
echo "ECS:         ${ECS_CLUSTER}/${ECS_SERVICE}"
echo "Log Group:   ${LOG_GROUP}"

echo
echo "[1/5] SNS Topic bereitstellen ..."
TOPIC_ARN=$(aws sns create-topic \
  --region "$AWS_REGION" \
  --name "$SNS_TOPIC_NAME" \
  --query 'TopicArn' \
  --output text)
echo "Topic ARN: ${TOPIC_ARN}"

if [[ -n "$ALERT_EMAIL" ]]; then
  echo
  echo "[1b/5] E-Mail Subscription anlegen (falls noch nicht vorhanden) ..."
  EXISTING_SUB=$(aws sns list-subscriptions-by-topic \
    --region "$AWS_REGION" \
    --topic-arn "$TOPIC_ARN" \
    --query "Subscriptions[?Protocol=='email' && Endpoint=='${ALERT_EMAIL}'] | [0].SubscriptionArn" \
    --output text)

  if [[ -z "$EXISTING_SUB" || "$EXISTING_SUB" == "None" ]]; then
    aws sns subscribe \
      --region "$AWS_REGION" \
      --topic-arn "$TOPIC_ARN" \
      --protocol email \
      --notification-endpoint "$ALERT_EMAIL" >/dev/null
    echo "Subscription angelegt. Bestätigungsmail an ${ALERT_EMAIL} versendet."
  else
    echo "Subscription bereits vorhanden (${EXISTING_SUB})."
  fi
fi

echo
echo "[2/5] Metric Filters für Request-Volumen + 5xx anlegen ..."
aws logs put-metric-filter \
  --region "$AWS_REGION" \
  --log-group-name "$LOG_GROUP" \
  --filter-name "swisstopo-dev-api-http-total" \
  --filter-pattern '[ip, ident, user, ts, request, status_code, bytes]' \
  --metric-transformations metricName=HttpRequestCount,metricNamespace="$METRIC_NAMESPACE",metricValue=1,defaultValue=0

aws logs put-metric-filter \
  --region "$AWS_REGION" \
  --log-group-name "$LOG_GROUP" \
  --filter-name "swisstopo-dev-api-http-5xx" \
  --filter-pattern '[ip, ident, user, ts, request, status_code = 5*, bytes]' \
  --metric-transformations metricName=Http5xxCount,metricNamespace="$METRIC_NAMESPACE",metricValue=1,defaultValue=0

echo "Metric Filters aktualisiert."

echo
echo "[3/5] Alarm: Service-Ausfall (RunningTaskCount < 1) ..."
aws cloudwatch put-metric-alarm \
  --region "$AWS_REGION" \
  --alarm-name "swisstopo-dev-api-running-taskcount-low" \
  --alarm-description "ECS service unhealthy: running tasks < 1" \
  --alarm-actions "$TOPIC_ARN" \
  --ok-actions "$TOPIC_ARN" \
  --namespace AWS/ECS \
  --metric-name RunningTaskCount \
  --dimensions Name=ClusterName,Value="$ECS_CLUSTER" Name=ServiceName,Value="$ECS_SERVICE" \
  --statistic Minimum \
  --period 60 \
  --evaluation-periods 3 \
  --datapoints-to-alarm 3 \
  --threshold 1 \
  --comparison-operator LessThanThreshold \
  --treat-missing-data breaching

echo
echo "[4/5] Alarm: API-Fehlerquote (5xx%) ..."
aws cloudwatch put-metric-alarm \
  --region "$AWS_REGION" \
  --alarm-name "swisstopo-dev-api-http-5xx-rate-high" \
  --alarm-description "API error rate too high: 5xx ratio > 5% (min 20 req/5m)" \
  --alarm-actions "$TOPIC_ARN" \
  --ok-actions "$TOPIC_ARN" \
  --evaluation-periods 2 \
  --datapoints-to-alarm 2 \
  --treat-missing-data notBreaching \
  --metrics "[
    {\"Id\":\"m5\",\"MetricStat\":{\"Metric\":{\"Namespace\":\"${METRIC_NAMESPACE}\",\"MetricName\":\"Http5xxCount\"},\"Period\":300,\"Stat\":\"Sum\"},\"ReturnData\":false},
    {\"Id\":\"mt\",\"MetricStat\":{\"Metric\":{\"Namespace\":\"${METRIC_NAMESPACE}\",\"MetricName\":\"HttpRequestCount\"},\"Period\":300,\"Stat\":\"Sum\"},\"ReturnData\":false},
    {\"Id\":\"er\",\"Expression\":\"IF(mt>=20,(m5/mt)*100,0)\",\"Label\":\"Http5xxRatePercent\",\"ReturnData\":true}
  ]" \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold

echo
echo "[5/5] Alarm-Kanal Test (SNS Publish) ..."
TEST_MESSAGE_ID=$(aws sns publish \
  --region "$AWS_REGION" \
  --topic-arn "$TOPIC_ARN" \
  --subject "swisstopo-dev monitoring baseline test" \
  --message "Monitoring baseline test message $(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --query 'MessageId' \
  --output text)

echo "SNS test message id: ${TEST_MESSAGE_ID}"

echo
echo "Fertig. Baseline aktiv:"
echo "- Alarm swisstopo-dev-api-running-taskcount-low"
echo "- Alarm swisstopo-dev-api-http-5xx-rate-high"
echo "- SNS Kanal ${TOPIC_ARN}"

if [[ -n "$ALERT_EMAIL" ]]; then
  echo "- Subscription endpoint (email): ${ALERT_EMAIL}"
else
  echo "- Hinweis: Kein ALERT_EMAIL gesetzt. Topic ist aktiv, aber ohne bestätigten externen Subscriber."
fi
