#!/usr/bin/env bash
set -euo pipefail

AWS_REGION="${AWS_REGION:-eu-central-1}"
ECS_CLUSTER_NAME="${ECS_CLUSTER_NAME:-swisstopo-dev}"
ECR_REPO_NAME="${ECR_REPO_NAME:-swisstopo-dev-api}"
LOG_GROUP_NAME="${LOG_GROUP_NAME:-/swisstopo/dev/ecs/api}"
S3_BUCKET_NAME="${S3_BUCKET_NAME:-swisstopo-dev-523234426229}"
TF_DIR="${TF_DIR:-infra/terraform}"

if ! command -v aws >/dev/null 2>&1; then
  echo "Fehler: aws CLI nicht gefunden." >&2
  exit 1
fi

echo "== Import-first Precheck (read-only) =="
echo "Region: ${AWS_REGION}"
echo

ACCOUNT_ARN=$(aws sts get-caller-identity --query 'Arn' --output text)
ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)

echo "Caller:  ${ACCOUNT_ARN}"
echo "Account: ${ACCOUNT_ID}"
echo

ECS_ARN=$(aws ecs describe-clusters \
  --region "${AWS_REGION}" \
  --clusters "${ECS_CLUSTER_NAME}" \
  --query 'clusters[0].clusterArn' \
  --output text)

ECS_STATUS=$(aws ecs describe-clusters \
  --region "${AWS_REGION}" \
  --clusters "${ECS_CLUSTER_NAME}" \
  --query 'clusters[0].status' \
  --output text)

ECS_CONTAINER_INSIGHTS=$(aws ecs describe-clusters \
  --region "${AWS_REGION}" \
  --clusters "${ECS_CLUSTER_NAME}" \
  --include SETTINGS \
  --query "clusters[0].settings[?name=='containerInsights'] | [0].value" \
  --output text)

ECR_ARN=$(aws ecr describe-repositories \
  --region "${AWS_REGION}" \
  --repository-names "${ECR_REPO_NAME}" \
  --query 'repositories[0].repositoryArn' \
  --output text)

ECR_URI=$(aws ecr describe-repositories \
  --region "${AWS_REGION}" \
  --repository-names "${ECR_REPO_NAME}" \
  --query 'repositories[0].repositoryUri' \
  --output text)

LOG_GROUP_FOUND=$(aws logs describe-log-groups \
  --region "${AWS_REGION}" \
  --log-group-name-prefix "${LOG_GROUP_NAME}" \
  --query "logGroups[?logGroupName=='${LOG_GROUP_NAME}'] | [0].logGroupName" \
  --output text)

LOG_GROUP_ARN=$(aws logs describe-log-groups \
  --region "${AWS_REGION}" \
  --log-group-name-prefix "${LOG_GROUP_NAME}" \
  --query "logGroups[?logGroupName=='${LOG_GROUP_NAME}'] | [0].arn" \
  --output text)

LOG_RETENTION=$(aws logs describe-log-groups \
  --region "${AWS_REGION}" \
  --log-group-name-prefix "${LOG_GROUP_NAME}" \
  --query "logGroups[?logGroupName=='${LOG_GROUP_NAME}'] | [0].retentionInDays" \
  --output text)

if aws s3api head-bucket --bucket "${S3_BUCKET_NAME}" >/dev/null 2>&1; then
  S3_BUCKET_EXISTS="true"
  S3_BUCKET_ARN="arn:aws:s3:::${S3_BUCKET_NAME}"
else
  S3_BUCKET_EXISTS="false"
  S3_BUCKET_ARN=""
fi

if [[ -z "${ECS_ARN}" || "${ECS_ARN}" == "None" || -z "${ECR_ARN}" || "${ECR_ARN}" == "None" || -z "${LOG_GROUP_FOUND}" || "${LOG_GROUP_FOUND}" == "None" || "${S3_BUCKET_EXISTS}" != "true" ]]; then
  echo "Fehler: Mindestens eine Zielressource wurde nicht gefunden." >&2
  echo "ECS ARN: ${ECS_ARN}" >&2
  echo "ECR ARN: ${ECR_ARN}" >&2
  echo "Log Group: ${LOG_GROUP_FOUND}" >&2
  echo "S3 Bucket: ${S3_BUCKET_NAME} (exists=${S3_BUCKET_EXISTS})" >&2
  exit 2
fi

echo "== Verifizierter Ist-Stand =="
echo "ECS Cluster:        ${ECS_CLUSTER_NAME}"
echo "  ARN:              ${ECS_ARN}"
echo "  Status:           ${ECS_STATUS}"
echo "  containerInsights:${ECS_CONTAINER_INSIGHTS}"
echo "ECR Repository:     ${ECR_REPO_NAME}"
echo "  ARN:              ${ECR_ARN}"
echo "  URI:              ${ECR_URI}"
echo "CW Log Group:       ${LOG_GROUP_FOUND}"
echo "  ARN:              ${LOG_GROUP_ARN}"
echo "  Retention:        ${LOG_RETENTION}"
echo "S3 Bucket:          ${S3_BUCKET_NAME}"
echo "  ARN:              ${S3_BUCKET_ARN}"
echo

echo "== Terraform Import-Kommandos =="
echo "terraform -chdir=${TF_DIR} import 'aws_ecs_cluster.dev[0]' ${ECS_CLUSTER_NAME}"
echo "terraform -chdir=${TF_DIR} import 'aws_ecr_repository.api[0]' ${ECR_REPO_NAME}"
echo "terraform -chdir=${TF_DIR} import 'aws_cloudwatch_log_group.api[0]' ${LOG_GROUP_FOUND}"
echo "terraform -chdir=${TF_DIR} import 'aws_s3_bucket.dev[0]' ${S3_BUCKET_NAME}"
echo

if [[ "${ECS_CONTAINER_INSIGHTS}" == "enabled" ]]; then
  ECS_CONTAINER_INSIGHTS_BOOL="true"
else
  ECS_CONTAINER_INSIGHTS_BOOL="false"
fi

echo "== Empfohlene tfvars-Werte (drift-arm) =="
echo "managed_by = \"openclaw\""
echo "ecs_container_insights_enabled = ${ECS_CONTAINER_INSIGHTS_BOOL}"
echo "cloudwatch_log_group_name = \"${LOG_GROUP_FOUND}\""
echo "cloudwatch_log_retention_days = ${LOG_RETENTION}"
echo "s3_bucket_name = \"${S3_BUCKET_NAME}\""
echo "existing_s3_bucket_name = \"${S3_BUCKET_NAME}\""
echo

echo "Hinweis: Script ist read-only. Es führt keinen terraform import/apply aus."
