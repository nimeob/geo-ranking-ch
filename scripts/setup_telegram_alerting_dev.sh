#!/usr/bin/env bash
# setup_telegram_alerting_dev.sh
# ─────────────────────────────────────────────────────────────────────────────
# Richtet Telegram-Alerting für swisstopo-dev ein:
#   1. SSM-Parameter mit Bot-Token anlegen (SecureString)
#   2. [Optional] Lambda manuell deployen (Fallback ohne Terraform)
#
# Benötigte Umgebungsvariablen:
#   TELEGRAM_BOT_TOKEN   – Bot-Token (Pflicht, NICHT im Repo speichern!)
#   TELEGRAM_CHAT_ID     – Ziel-Chat-ID (Pflicht, z.B. 8614377280)
#
# Optionale Umgebungsvariablen:
#   AWS_REGION           – Default: eu-central-1
#   SNS_TOPIC_ARN        – Default: arn:aws:sns:eu-central-1:523234426229:swisstopo-dev-alerts
#   LAMBDA_FUNCTION_NAME – Default: swisstopo-dev-sns-to-telegram
#   SSM_PARAM_NAME       – Default: /swisstopo/dev/telegram-bot-token
#   SKIP_LAMBDA_DEPLOY   – Auf "true" setzen, um Lambda-Deploy zu überspringen (nur SSM)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

AWS_REGION="${AWS_REGION:-eu-central-1}"
SNS_TOPIC_ARN="${SNS_TOPIC_ARN:-arn:aws:sns:eu-central-1:523234426229:swisstopo-dev-alerts}"
LAMBDA_FUNCTION_NAME="${LAMBDA_FUNCTION_NAME:-swisstopo-dev-sns-to-telegram}"
SSM_PARAM_NAME="${SSM_PARAM_NAME:-/swisstopo/dev/telegram-bot-token}"
SKIP_LAMBDA_DEPLOY="${SKIP_LAMBDA_DEPLOY:-false}"
ACCOUNT_ID="523234426229"
ENVIRONMENT="dev"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAMBDA_SRC="${SCRIPT_DIR}/../infra/lambda/sns_to_telegram/lambda_function.py"
LAMBDA_ZIP="/tmp/sns_to_telegram_$$.zip"

# ─────────────────────────────────────────────────────────────────────────────
if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  echo "❌ Fehler: TELEGRAM_BOT_TOKEN muss als Umgebungsvariable gesetzt sein." >&2
  echo "   Beispiel: TELEGRAM_BOT_TOKEN='...' TELEGRAM_CHAT_ID='...' $0" >&2
  exit 1
fi

if [[ -z "${TELEGRAM_CHAT_ID:-}" ]]; then
  echo "❌ Fehler: TELEGRAM_CHAT_ID muss als Umgebungsvariable gesetzt sein." >&2
  exit 1
fi

echo "== Telegram-Alerting Setup (swisstopo-${ENVIRONMENT}) =="
echo "Region:          ${AWS_REGION}"
echo "SNS Topic:       ${SNS_TOPIC_ARN}"
echo "Lambda:          ${LAMBDA_FUNCTION_NAME}"
echo "SSM-Parameter:   ${SSM_PARAM_NAME}"
echo "Chat-ID:         ${TELEGRAM_CHAT_ID}"
echo

# ── 1) AWS-Credentials prüfen ────────────────────────────────────────────────
if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo "❌ AWS Credentials nicht verfügbar." >&2
  exit 2
fi
echo "✅ AWS Credentials OK"

# ── 2) SSM-Parameter anlegen / aktualisieren (SecureString) ──────────────────
echo ""
echo "→ SSM-Parameter anlegen/aktualisieren..."
aws ssm put-parameter \
  --region "$AWS_REGION" \
  --name "$SSM_PARAM_NAME" \
  --type SecureString \
  --value "$TELEGRAM_BOT_TOKEN" \
  --description "Telegram Bot Token für ${LAMBDA_FUNCTION_NAME} (swisstopo-${ENVIRONMENT} alerting)" \
  --overwrite \
  --tags \
    "Key=Environment,Value=${ENVIRONMENT}" \
    "Key=ManagedBy,Value=openclaw" \
    "Key=Owner,Value=nico" \
    "Key=Project,Value=swisstopo" \
  2>&1 | grep -v "Token\|token\|secret\|Secret" || true

# Wert NICHT loggen — nur prüfen ob erfolgreich
ssm_name=$(aws ssm get-parameter \
  --region "$AWS_REGION" \
  --name "$SSM_PARAM_NAME" \
  --query 'Parameter.Name' \
  --output text 2>/dev/null || true)

if [[ "$ssm_name" == "$SSM_PARAM_NAME" ]]; then
  echo "✅ SSM-Parameter vorhanden: ${SSM_PARAM_NAME}"
else
  echo "❌ SSM-Parameter konnte nicht angelegt werden" >&2
  exit 3
fi

# ── 3) Lambda deployen (optional, Fallback ohne Terraform) ───────────────────
if [[ "${SKIP_LAMBDA_DEPLOY}" == "true" ]]; then
  echo ""
  echo "ℹ️  Lambda-Deploy übersprungen (SKIP_LAMBDA_DEPLOY=true)."
  echo "   Verwende Terraform (manage_telegram_alerting=true) für den vollständigen Deploy."
  exit 0
fi

echo ""
echo "→ Lambda-Funktion deployen..."

# Lambda-Source zippen
if ! command -v zip >/dev/null 2>&1; then
  echo "❌ 'zip' nicht gefunden — Lambda-Deploy nicht möglich ohne Terraform." >&2
  echo "   Installiere zip oder verwende manage_telegram_alerting=true in Terraform." >&2
  exit 4
fi

zip -j "$LAMBDA_ZIP" "$LAMBDA_SRC"
echo "✅ Lambda-ZIP erstellt: ${LAMBDA_ZIP}"

# IAM-Role prüfen/erstellen (minimal)
ROLE_NAME="swisstopo-${ENVIRONMENT}-sns-to-telegram-role"
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

if ! aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  echo "→ IAM-Role anlegen: ${ROLE_NAME}"
  TRUST_DOC='{"Version":"2012-10-17","Statement":[{"Sid":"LambdaAssumeRole","Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
  aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document "$TRUST_DOC" \
    --description "Lambda-Execution-Role für Telegram-Alerting (swisstopo-${ENVIRONMENT})" \
    --tags \
      "Key=Environment,Value=${ENVIRONMENT}" \
      "Key=ManagedBy,Value=openclaw" \
      "Key=Owner,Value=nico" \
      "Key=Project,Value=swisstopo" \
    >/dev/null
  echo "✅ IAM-Role erstellt"

  # Inline-Policy anhängen
  POLICY_DOC=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCloudWatchLogs",
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],
      "Resource": "arn:aws:logs:${AWS_REGION}:${ACCOUNT_ID}:log-group:/aws/lambda/${LAMBDA_FUNCTION_NAME}:*"
    },
    {
      "Sid": "AllowSSMGetBotToken",
      "Effect": "Allow",
      "Action": ["ssm:GetParameter"],
      "Resource": "arn:aws:ssm:${AWS_REGION}:${ACCOUNT_ID}:parameter${SSM_PARAM_NAME}"
    },
    {
      "Sid": "AllowKMSDecryptSSMKey",
      "Effect": "Allow",
      "Action": ["kms:Decrypt"],
      "Resource": "arn:aws:kms:${AWS_REGION}:${ACCOUNT_ID}:key/aws/ssm"
    }
  ]
}
EOF
)
  aws iam put-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name "sns-to-telegram-inline" \
    --policy-document "$POLICY_DOC" \
    >/dev/null
  echo "✅ IAM Inline-Policy gesetzt"

  echo "→ Warte kurz auf IAM-Role-Propagation..."
  sleep 10
else
  echo "✅ IAM-Role bereits vorhanden: ${ROLE_NAME}"
fi

# Lambda anlegen oder aktualisieren
if aws lambda get-function --region "$AWS_REGION" --function-name "$LAMBDA_FUNCTION_NAME" >/dev/null 2>&1; then
  echo "→ Lambda-Funktion aktualisieren..."
  aws lambda update-function-code \
    --region "$AWS_REGION" \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --zip-file "fileb://${LAMBDA_ZIP}" \
    --output text --query 'FunctionArn' | xargs echo "  ARN:"

  aws lambda update-function-configuration \
    --region "$AWS_REGION" \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --environment "Variables={TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID},TELEGRAM_BOT_TOKEN_SSM=${SSM_PARAM_NAME}}" \
    --output text --query 'FunctionArn' >/dev/null
  echo "✅ Lambda aktualisiert"
else
  echo "→ Lambda-Funktion neu anlegen..."
  LAMBDA_ARN=$(aws lambda create-function \
    --region "$AWS_REGION" \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --description "Forwardiert CloudWatch-Alarme via SNS als Telegram-Nachricht" \
    --role "$ROLE_ARN" \
    --zip-file "fileb://${LAMBDA_ZIP}" \
    --handler "lambda_function.lambda_handler" \
    --runtime "python3.12" \
    --timeout 30 \
    --memory-size 128 \
    --environment "Variables={TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID},TELEGRAM_BOT_TOKEN_SSM=${SSM_PARAM_NAME}}" \
    --tags \
      "Environment=${ENVIRONMENT}" \
      "ManagedBy=openclaw" \
      "Owner=nico" \
      "Project=swisstopo" \
    --query 'FunctionArn' \
    --output text)
  echo "✅ Lambda angelegt: ${LAMBDA_ARN}"
fi

LAMBDA_ARN=$(aws lambda get-function \
  --region "$AWS_REGION" \
  --function-name "$LAMBDA_FUNCTION_NAME" \
  --query 'Configuration.FunctionArn' \
  --output text)

# ── 4) Lambda-Permission für SNS ─────────────────────────────────────────────
echo ""
echo "→ Lambda-Permission für SNS setzen..."
aws lambda add-permission \
  --region "$AWS_REGION" \
  --function-name "$LAMBDA_FUNCTION_NAME" \
  --statement-id "AllowSNSInvoke" \
  --action "lambda:InvokeFunction" \
  --principal "sns.amazonaws.com" \
  --source-arn "$SNS_TOPIC_ARN" \
  >/dev/null 2>&1 || echo "  (Permission bereits vorhanden — OK)"
echo "✅ Lambda-Permission gesetzt"

# ── 5) SNS → Lambda Subscription ─────────────────────────────────────────────
echo ""
echo "→ SNS → Lambda Subscription anlegen..."
existing_sub=$(aws sns list-subscriptions-by-topic \
  --region "$AWS_REGION" \
  --topic-arn "$SNS_TOPIC_ARN" \
  --query "Subscriptions[?Protocol=='lambda' && Endpoint=='${LAMBDA_ARN}'].SubscriptionArn" \
  --output text 2>/dev/null || true)

if [[ -n "$existing_sub" && "$existing_sub" != "None" ]]; then
  echo "✅ SNS-Subscription bereits vorhanden: ${existing_sub}"
else
  SUB_ARN=$(aws sns subscribe \
    --region "$AWS_REGION" \
    --topic-arn "$SNS_TOPIC_ARN" \
    --protocol lambda \
    --notification-endpoint "$LAMBDA_ARN" \
    --query 'SubscriptionArn' \
    --output text)
  echo "✅ SNS-Subscription erstellt: ${SUB_ARN}"
fi

# ── Cleanup ───────────────────────────────────────────────────────────────────
rm -f "$LAMBDA_ZIP"

echo ""
echo "======================================================================"
echo "✅ Telegram-Alerting Setup abgeschlossen."
echo ""
echo "Testalarm ausloesen:"
echo "  aws cloudwatch set-alarm-state \\"
echo "    --region ${AWS_REGION} \\"
echo "    --alarm-name swisstopo-dev-api-running-taskcount-low \\"
echo "    --state-value ALARM \\"
echo "    --state-reason 'Kontrollierter Testalarm via set-alarm-state'"
echo ""
echo "Danach Reset:"
echo "  aws cloudwatch set-alarm-state \\"
echo "    --region ${AWS_REGION} \\"
echo "    --alarm-name swisstopo-dev-api-running-taskcount-low \\"
echo "    --state-value OK \\"
echo "    --state-reason 'Reset nach Testalarm'"
echo "======================================================================"
