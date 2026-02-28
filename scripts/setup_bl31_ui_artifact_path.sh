#!/usr/bin/env bash
# setup_bl31_ui_artifact_path.sh
# BL-31.6.a: ECR-Artefaktpfad + Task-Revision für UI vorbereiten (dev)
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

require_bin() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "ERROR: required binary not found: $bin" >&2
    exit 2
  fi
}

require_bin aws
require_bin python3
require_bin git

AWS_REGION="${AWS_REGION:-eu-central-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
ECR_REPOSITORY="${ECR_REPOSITORY:-swisstopo-dev-ui}"
CODEBUILD_PROJECT="${CODEBUILD_PROJECT:-swisstopo-dev-api-openclaw-build}"
CODEBUILD_SOURCE_S3_URI="${CODEBUILD_SOURCE_S3_URI:-s3://swisstopo-dev-523234426229/codebuild-src/geo-ranking-ch-main.zip}"
DOCKERFILE_PATH="${DOCKERFILE_PATH:-Dockerfile.ui}"
UI_API_BASE_URL="${UI_API_BASE_URL:-https://api.dev.invalid}"
IMAGE_TAG="${IMAGE_TAG:-ui345-$(TZ=Europe/Berlin date +%Y%m%d%H%M%S)-$(git rev-parse --short HEAD)}"
APP_VERSION="${APP_VERSION:-${IMAGE_TAG}}"
TASKDEF_TEMPLATE="${TASKDEF_TEMPLATE:-infra/ecs/taskdef.swisstopo-dev-ui.json}"
UI_DOMAIN="${UI_DOMAIN:-dev.invalid}"
ASSUME_ROLE_ARN="${ASSUME_ROLE_ARN:-arn:aws:iam::523234426229:role/openclaw-ops-role}"
ASSUME_ROLE_DURATION="${ASSUME_ROLE_DURATION:-900}"
POLL_SECONDS="${POLL_SECONDS:-20}"
OUT_DIR="${OUT_DIR:-artifacts/bl31}"

mkdir -p "${OUT_DIR}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SUMMARY_JSON="${OUT_DIR}/${STAMP}-bl31-ui-artifact-path.json"

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

echo "[1/6] Ensure ECR repository exists: ${ECR_REPOSITORY}"
if ! aws ecr describe-repositories --region "${AWS_REGION}" --repository-names "${ECR_REPOSITORY}" >/dev/null 2>&1; then
  aws ecr create-repository \
    --region "${AWS_REGION}" \
    --repository-name "${ECR_REPOSITORY}" \
    --image-scanning-configuration scanOnPush=true >/dev/null
fi

echo "[2/6] Ensure ECR repository policy allows CodeBuild push"
cat >"${TMP_DIR}/ecr_policy.json" <<JSON
{
  "Version": "2008-10-17",
  "Statement": [
    {
      "Sid": "AllowCodeBuildPushPull",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::${AWS_ACCOUNT_ID}:role/swisstopo-dev-openclaw-codebuild-role"
      },
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:BatchGetImage",
        "ecr:CompleteLayerUpload",
        "ecr:GetDownloadUrlForLayer",
        "ecr:InitiateLayerUpload",
        "ecr:PutImage",
        "ecr:UploadLayerPart"
      ]
    }
  ]
}
JSON
aws ecr set-repository-policy \
  --region "${AWS_REGION}" \
  --repository-name "${ECR_REPOSITORY}" \
  --policy-text "file://${TMP_DIR}/ecr_policy.json" >/dev/null

echo "[3/6] Upload source zip for CodeBuild"
python3 - <<'PY' "${TMP_DIR}" "${REPO_ROOT}"
import os
import subprocess
import sys
import zipfile

tmp_dir, repo_root = sys.argv[1:3]
out = os.path.join(tmp_dir, "geo-ranking-ch-main.zip")
raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=repo_root)
paths = [p for p in raw.decode("utf-8").split("\x00") if p]
if "buildspec-openclaw.yml" not in paths and os.path.exists(os.path.join(repo_root, "buildspec-openclaw.yml")):
    paths.append("buildspec-openclaw.yml")
with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for rel in paths:
        zf.write(os.path.join(repo_root, rel), rel)
print(out)
PY
aws s3 cp "${TMP_DIR}/geo-ranking-ch-main.zip" "${CODEBUILD_SOURCE_S3_URI}" --region "${AWS_REGION}" >/dev/null

echo "[4/6] Start and wait for CodeBuild image push"
BUILD_ID="$(aws codebuild start-build \
  --region "${AWS_REGION}" \
  --project-name "${CODEBUILD_PROJECT}" \
  --environment-variables-override \
    name=AWS_ACCOUNT_ID,value="${AWS_ACCOUNT_ID}",type=PLAINTEXT \
    name=AWS_REGION,value="${AWS_REGION}",type=PLAINTEXT \
    name=ECR_REPOSITORY,value="${ECR_REPOSITORY}",type=PLAINTEXT \
    name=DOCKERFILE_PATH,value="${DOCKERFILE_PATH}",type=PLAINTEXT \
    name=UI_API_BASE_URL,value="${UI_API_BASE_URL}",type=PLAINTEXT \
    name=IMAGE_TAG,value="${IMAGE_TAG}",type=PLAINTEXT \
    name=APP_VERSION,value="${APP_VERSION}",type=PLAINTEXT \
  --query 'build.id' --output text)"

while true; do
  BUILD_STATUS="$(aws codebuild batch-get-builds --region "${AWS_REGION}" --ids "${BUILD_ID}" --query 'builds[0].buildStatus' --output text)"
  BUILD_PHASE="$(aws codebuild batch-get-builds --region "${AWS_REGION}" --ids "${BUILD_ID}" --query 'builds[0].currentPhase' --output text)"
  echo "  - ${BUILD_ID}: status=${BUILD_STATUS} phase=${BUILD_PHASE}"
  case "${BUILD_STATUS}" in
    SUCCEEDED|FAILED|FAULT|STOPPED|TIMED_OUT)
      break
      ;;
  esac
  sleep "${POLL_SECONDS}"
done

LOG_GROUP="$(aws codebuild batch-get-builds --region "${AWS_REGION}" --ids "${BUILD_ID}" --query 'builds[0].logs.groupName' --output text)"
LOG_STREAM="$(aws codebuild batch-get-builds --region "${AWS_REGION}" --ids "${BUILD_ID}" --query 'builds[0].logs.streamName' --output text)"

if [[ "${BUILD_STATUS}" != "SUCCEEDED" ]]; then
  echo "ERROR: CodeBuild failed (${BUILD_STATUS}). Logs: ${LOG_GROUP} / ${LOG_STREAM}" >&2
  exit 10
fi

IMAGE_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}"
set +e
IMAGE_DIGEST="$(aws ecr describe-images --region "${AWS_REGION}" --repository-name "${ECR_REPOSITORY}" --image-ids imageTag="${IMAGE_TAG}" --query 'imageDetails[0].imageDigest' --output text 2>"${TMP_DIR}/describe-image.err")"
DIGEST_RC=$?
set -e

if [[ ${DIGEST_RC} -ne 0 || -z "${IMAGE_DIGEST}" || "${IMAGE_DIGEST}" == "None" || "${IMAGE_DIGEST}" == "null" ]]; then
  echo "  - WARN: expected image tag ${IMAGE_TAG} not found; fallback to latest pushed tag in ${ECR_REPOSITORY}"
  IMAGE_TAG="$(aws ecr describe-images --region "${AWS_REGION}" --repository-name "${ECR_REPOSITORY}" --query 'sort_by(imageDetails,&imagePushedAt)[-1].imageTags[0]' --output text)"
  IMAGE_DIGEST="$(aws ecr describe-images --region "${AWS_REGION}" --repository-name "${ECR_REPOSITORY}" --query 'sort_by(imageDetails,&imagePushedAt)[-1].imageDigest' --output text)"
  IMAGE_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}"
  APP_VERSION="${IMAGE_TAG}"
fi

echo "[5/6] Register ECS task definition revision"
sed -e "s|__IMAGE_TAG__|${IMAGE_TAG}|g" \
    -e "s|__APP_VERSION__|${APP_VERSION}|g" \
    -e "s|__DOMAIN__|${UI_DOMAIN}|g" \
    "${TASKDEF_TEMPLATE}" > "${TMP_DIR}/taskdef-rendered.json"

set +e
TASKDEF_ARN="$(aws ecs register-task-definition --region "${AWS_REGION}" --cli-input-json "file://${TMP_DIR}/taskdef-rendered.json" --query 'taskDefinition.taskDefinitionArn' --output text 2>"${TMP_DIR}/register.err")"
REG_RC=$?
set -e

if [[ ${REG_RC} -ne 0 ]]; then
  if grep -q 'AccessDenied' "${TMP_DIR}/register.err"; then
    echo "  - Current IAM principal lacks ecs:RegisterTaskDefinition; retry via assume-role ${ASSUME_ROLE_ARN}"
    CREDS="$(aws sts assume-role --role-arn "${ASSUME_ROLE_ARN}" --role-session-name "bl31-ui-taskdef-${STAMP}" --duration-seconds "${ASSUME_ROLE_DURATION}" --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' --output text)"
    read -r ASSUME_AK ASSUME_SK ASSUME_ST <<<"${CREDS}"
    TASKDEF_ARN="$(AWS_ACCESS_KEY_ID="${ASSUME_AK}" AWS_SECRET_ACCESS_KEY="${ASSUME_SK}" AWS_SESSION_TOKEN="${ASSUME_ST}" aws ecs register-task-definition --region "${AWS_REGION}" --cli-input-json "file://${TMP_DIR}/taskdef-rendered.json" --query 'taskDefinition.taskDefinitionArn' --output text)"
  else
    cat "${TMP_DIR}/register.err" >&2
    exit ${REG_RC}
  fi
fi

TASKDEF_IMAGE="$(aws ecs describe-task-definition --region "${AWS_REGION}" --task-definition "${TASKDEF_ARN}" --query 'taskDefinition.containerDefinitions[0].image' --output text)"

echo "[6/6] Write evidence summary"
python3 - <<'PY' "${SUMMARY_JSON}" "${BUILD_ID}" "${BUILD_STATUS}" "${LOG_GROUP}" "${LOG_STREAM}" "${IMAGE_URI}" "${IMAGE_DIGEST}" "${TASKDEF_ARN}" "${TASKDEF_IMAGE}" "${UI_DOMAIN}" "${CODEBUILD_SOURCE_S3_URI}"
import json
import pathlib
import sys

(
    out,
    build_id,
    build_status,
    log_group,
    log_stream,
    image_uri,
    image_digest,
    taskdef_arn,
    taskdef_image,
    ui_domain,
    source_s3_uri,
) = sys.argv[1:]

payload = {
    "build": {
        "id": build_id,
        "status": build_status,
        "logGroup": log_group,
        "logStream": log_stream,
        "sourceS3": source_s3_uri,
    },
    "image": {
        "uri": image_uri,
        "digest": image_digest,
    },
    "taskDefinition": {
        "arn": taskdef_arn,
        "image": taskdef_image,
        "uiDomain": ui_domain,
    },
}
path = pathlib.Path(out)
path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(path)
PY

echo "Done. Evidence: ${SUMMARY_JSON}"
