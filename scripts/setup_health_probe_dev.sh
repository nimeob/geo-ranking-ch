#!/usr/bin/env bash
# setup_health_probe_dev.sh
# Idempotentes Setup der HTTP-Uptime-Probe (default: swisstopo-dev GET /health).
#
# Was wird erstellt:
#   1. IAM-Role  swisstopo-dev-health-probe-role
#   2. Lambda    swisstopo-dev-health-probe  (aus infra/lambda/health_probe/)
#   3. EventBridge-Rule  swisstopo-dev-health-probe-schedule  (alle 5 Min)
#   4. CloudWatch Alarm  swisstopo-dev-api-health-probe-fail  → SNS
#
# Sicher auszuführen: idempotent, keine destruktiven Änderungen.
# Bei erneutem Ausführen werden vorhandene Ressourcen aktualisiert (not replaced).
#
# Voraussetzungen:
#   - aws CLI, python3 (zip via stdlib)
#   - IAM-Rechte: iam:CreateRole, iam:AttachRolePolicy, iam:PutRolePolicy,
#                 lambda:CreateFunction/UpdateFunctionCode/UpdateFunctionConfiguration,
#                 events:PutRule/PutTargets, cloudwatch:PutMetricAlarm

set -euo pipefail

# ── Konfiguration ────────────────────────────────────────────────────────────
AWS_REGION="${AWS_REGION:-eu-central-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-523234426229}"
ECS_CLUSTER="${ECS_CLUSTER:-swisstopo-dev}"
ECS_SERVICE="${ECS_SERVICE:-swisstopo-dev-api}"
HEALTH_PORT="${HEALTH_PORT:-8080}"
HEALTH_PATH="${HEALTH_PATH:-/health}"
METRIC_NS="${METRIC_NS:-swisstopo/dev-api}"
SNS_TOPIC_ARN="${SNS_TOPIC_ARN:-arn:aws:sns:eu-central-1:523234426229:swisstopo-dev-alerts}"

LAMBDA_NAME="${LAMBDA_NAME:-swisstopo-dev-health-probe}"
ROLE_NAME="${ROLE_NAME:-swisstopo-dev-health-probe-role}"
RULE_NAME="${RULE_NAME:-swisstopo-dev-health-probe-schedule}"
ALARM_NAME="${ALARM_NAME:-swisstopo-dev-api-health-probe-fail}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LAMBDA_SRC="${REPO_ROOT}/infra/lambda/health_probe"

# ── Vorbedingungen prüfen ────────────────────────────────────────────────────
for cmd in aws python3; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "❌ Fehler: '$cmd' nicht gefunden." >&2
    exit 1
  fi
done

echo "== HTTP Uptime Probe Setup (dev) =="
echo "Region:      ${AWS_REGION}"
echo "Account:     ${AWS_ACCOUNT_ID}"
echo "ECS:         ${ECS_CLUSTER}/${ECS_SERVICE}"
echo "Lambda:      ${LAMBDA_NAME}"
echo "SNS Topic:   ${SNS_TOPIC_ARN}"
echo

# ── 1. IAM Role ──────────────────────────────────────────────────────────────
echo "[1/5] IAM Role bereitstellen (${ROLE_NAME}) ..."

TRUST_POLICY='{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}'

ROLE_ARN=$(aws iam create-role \
  --role-name "$ROLE_NAME" \
  --assume-role-policy-document "$TRUST_POLICY" \
  --description "Health Probe Lambda: ECS task IP lookup + HTTP probe + CW metric" \
  --tags Key=Environment,Value=dev Key=ManagedBy,Value=openclaw Key=Owner,Value=nico Key=Project,Value=swisstopo \
  --query 'Role.Arn' \
  --output text 2>/dev/null) || \
ROLE_ARN=$(aws iam get-role \
  --role-name "$ROLE_NAME" \
  --query 'Role.Arn' \
  --output text)
echo "Role ARN: ${ROLE_ARN}"

# Managed policy für CloudWatch Logs (Lambda basic execution)
aws iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" \
  2>/dev/null || true

# Inline policy: ECS + EC2 IP-Lookup + CloudWatch PutMetricData
INLINE_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECSTaskLookup",
      "Effect": "Allow",
      "Action": [
        "ecs:ListTasks",
        "ecs:DescribeTasks"
      ],
      "Resource": "*",
      "Condition": {
        "ArnLike": {
          "ecs:cluster": "arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT_ID}:cluster/${ECS_CLUSTER}"
        }
      }
    },
    {
      "Sid": "ENIPublicIPLookup",
      "Effect": "Allow",
      "Action": "ec2:DescribeNetworkInterfaces",
      "Resource": "*"
    },
    {
      "Sid": "PutHealthMetric",
      "Effect": "Allow",
      "Action": "cloudwatch:PutMetricData",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "cloudwatch:namespace": "${METRIC_NS}"
        }
      }
    }
  ]
}
EOF
)
aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name "health-probe-inline" \
  --policy-document "$INLINE_POLICY"
echo "Inline Policy gesetzt."

# ── 2. Lambda ZIP bauen + deployen ───────────────────────────────────────────
echo
echo "[2/5] Lambda ZIP bauen und deployen (${LAMBDA_NAME}) ..."

TMPDIR_ZIP=$(mktemp -d)
cp "${LAMBDA_SRC}/lambda_function.py" "${TMPDIR_ZIP}/"
ZIP_PATH="${TMPDIR_ZIP}/health_probe.zip"
# zip via Python stdlib (kein externes 'zip' erforderlich)
python3 -c "
import zipfile, os
with zipfile.ZipFile('${ZIP_PATH}', 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.write('${TMPDIR_ZIP}/lambda_function.py', 'lambda_function.py')
print('ZIP erstellt.')
"
echo "ZIP: ${ZIP_PATH}"

# Wartepause für IAM eventual consistency (Role neu erstellt: bis zu 15s)
sleep 15

EXISTING_LAMBDA=$(aws lambda get-function \
  --region "$AWS_REGION" \
  --function-name "$LAMBDA_NAME" \
  --query 'Configuration.FunctionArn' \
  --output text 2>/dev/null || echo "NOT_FOUND")

if [[ "$EXISTING_LAMBDA" == "NOT_FOUND" ]]; then
  echo "Lambda noch nicht vorhanden — erstelle neu ..."
  LAMBDA_ARN=$(aws lambda create-function \
    --region "$AWS_REGION" \
    --function-name "$LAMBDA_NAME" \
    --runtime python3.12 \
    --role "$ROLE_ARN" \
    --handler lambda_function.lambda_handler \
    --zip-file "fileb://${ZIP_PATH}" \
    --timeout 30 \
    --memory-size 128 \
    --description "HTTP Uptime Probe: swisstopo-dev GET /health (dynamische ECS-IP)" \
    --environment "Variables={ECS_CLUSTER=${ECS_CLUSTER},ECS_SERVICE=${ECS_SERVICE},HEALTH_PORT=${HEALTH_PORT},HEALTH_PATH=${HEALTH_PATH},METRIC_NS=${METRIC_NS}}" \
    --tags Environment=dev,ManagedBy=openclaw,Owner=nico,Project=swisstopo \
    --query 'FunctionArn' \
    --output text)
  echo "Lambda erstellt: ${LAMBDA_ARN}"
else
  echo "Lambda bereits vorhanden — aktualisiere Code + Konfiguration ..."
  aws lambda update-function-code \
    --region "$AWS_REGION" \
    --function-name "$LAMBDA_NAME" \
    --zip-file "fileb://${ZIP_PATH}" >/dev/null
  sleep 3
  aws lambda update-function-configuration \
    --region "$AWS_REGION" \
    --function-name "$LAMBDA_NAME" \
    --runtime python3.12 \
    --role "$ROLE_ARN" \
    --timeout 30 \
    --memory-size 128 \
    --environment "Variables={ECS_CLUSTER=${ECS_CLUSTER},ECS_SERVICE=${ECS_SERVICE},HEALTH_PORT=${HEALTH_PORT},HEALTH_PATH=${HEALTH_PATH},METRIC_NS=${METRIC_NS}}" >/dev/null
  LAMBDA_ARN="$EXISTING_LAMBDA"
  echo "Lambda aktualisiert: ${LAMBDA_ARN}"
fi

rm -rf "$TMPDIR_ZIP"

# ── 3. EventBridge Rule (alle 5 Minuten) ─────────────────────────────────────
echo
echo "[3/5] EventBridge Scheduled Rule (${RULE_NAME}, rate=5min) ..."

RULE_ARN=$(aws events put-rule \
  --region "$AWS_REGION" \
  --name "$RULE_NAME" \
  --schedule-expression "rate(5 minutes)" \
  --description "Trigger HTTP health probe Lambda alle 5 Minuten" \
  --state ENABLED \
  --query 'RuleArn' \
  --output text)
echo "Rule ARN: ${RULE_ARN}"

# Lambda Permission für EventBridge (idempotent via remove + add)
aws lambda remove-permission \
  --region "$AWS_REGION" \
  --function-name "$LAMBDA_NAME" \
  --statement-id "allow-eventbridge-health-probe" \
  2>/dev/null || true

aws lambda add-permission \
  --region "$AWS_REGION" \
  --function-name "$LAMBDA_NAME" \
  --statement-id "allow-eventbridge-health-probe" \
  --action "lambda:InvokeFunction" \
  --principal "events.amazonaws.com" \
  --source-arn "$RULE_ARN" >/dev/null

aws events put-targets \
  --region "$AWS_REGION" \
  --rule "$RULE_NAME" \
  --targets "[{\"Id\": \"health-probe-lambda\", \"Arn\": \"${LAMBDA_ARN}\"}]" >/dev/null
echo "EventBridge Target gesetzt."

# ── 4. CloudWatch Alarm ───────────────────────────────────────────────────────
echo
echo "[4/5] CloudWatch Alarm (${ALARM_NAME}) ..."

# Alarm wenn HealthProbeSuccess in 3 von 3 Perioden (15 Min) = 0
# treat-missing-data=breaching: kein Metric-Datenpunkt = Alarm
aws cloudwatch put-metric-alarm \
  --region "$AWS_REGION" \
  --alarm-name "$ALARM_NAME" \
  --alarm-description "HTTP /health probe failed (ECS task not reachable or unhealthy)" \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --ok-actions "$SNS_TOPIC_ARN" \
  --namespace "$METRIC_NS" \
  --metric-name "HealthProbeSuccess" \
  --dimensions Name=Service,Value="$ECS_SERVICE" Name=Environment,Value=dev \
  --statistic Minimum \
  --period 300 \
  --evaluation-periods 3 \
  --datapoints-to-alarm 3 \
  --threshold 1 \
  --comparison-operator LessThanThreshold \
  --treat-missing-data breaching
echo "Alarm gesetzt."

# ── 5. Sofortiger Testlauf ───────────────────────────────────────────────────
echo
echo "[5/5] Sofortiger Lambda-Testlauf ..."
INVOKE_RESULT=$(aws lambda invoke \
  --region "$AWS_REGION" \
  --function-name "$LAMBDA_NAME" \
  --log-type Tail \
  /tmp/health_probe_invoke_result.json \
  --query 'StatusCode' \
  --output text 2>&1)

echo "Lambda invoke StatusCode: ${INVOKE_RESULT}"
PAYLOAD=$(cat /tmp/health_probe_invoke_result.json 2>/dev/null || echo "{}")
echo "Payload: ${PAYLOAD}"

if echo "$PAYLOAD" | grep -q '"ok": true\|"ok":true'; then
  echo "✅ Probe erfolgreich: /health erreichbar und HTTP 200"
elif echo "$PAYLOAD" | grep -q '"ok": false\|"ok":false'; then
  echo "⚠️  Probe: 'ok=false' — Task möglicherweise gerade nicht erreichbar"
  echo "   Das ist kein Setup-Fehler; Probe und Alarm sind dennoch eingerichtet."
fi

echo
echo "== Setup abgeschlossen =="
echo "Lambda:    ${LAMBDA_NAME}"
echo "Schedule:  alle 5 Minuten (EventBridge: ${RULE_NAME})"
echo "Alarm:     ${ALARM_NAME} → ${SNS_TOPIC_ARN}"
echo
echo "Metrik prüfen:"
echo "  aws cloudwatch get-metric-statistics \\"
echo "    --region ${AWS_REGION} \\"
echo "    --namespace '${METRIC_NS}' \\"
echo "    --metric-name HealthProbeSuccess \\"
echo "    --dimensions Name=Service,Value=${ECS_SERVICE} Name=Environment,Value=dev \\"
echo "    --start-time \$(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-30M +%Y-%m-%dT%H:%M:%SZ) \\"
echo "    --end-time \$(date -u +%Y-%m-%dT%H:%M:%SZ) \\"
echo "    --period 300 \\"
echo "    --statistics Minimum"
