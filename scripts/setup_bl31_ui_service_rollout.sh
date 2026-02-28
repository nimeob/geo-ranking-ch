#!/usr/bin/env bash
# setup_bl31_ui_service_rollout.sh
# BL-31.6.b: UI-Service in ECS dev ausrollen + Stabilisierung verifizieren.
set -euo pipefail

require_bin() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "ERROR: required binary not found: $bin" >&2
    exit 2
  fi
}

require_bin aws
require_bin curl
require_bin python3

AWS_REGION="${AWS_REGION:-eu-central-1}"
ECS_CLUSTER="${ECS_CLUSTER:-swisstopo-dev}"
UI_SERVICE="${UI_SERVICE:-swisstopo-dev-ui}"
API_SERVICE="${API_SERVICE:-swisstopo-dev-api}"
UI_TASKDEF_FAMILY="${UI_TASKDEF_FAMILY:-swisstopo-dev-ui}"
UI_CONTAINER_PORT="${UI_CONTAINER_PORT:-8080}"
API_CONTAINER_PORT="${API_CONTAINER_PORT:-8080}"
UI_HEALTH_PATH="${UI_HEALTH_PATH:-/healthz}"
API_HEALTH_PATH="${API_HEALTH_PATH:-/health}"
FORCE_NEW_DEPLOYMENT="${FORCE_NEW_DEPLOYMENT:-1}"
OUT_DIR="${OUT_DIR:-artifacts/bl31}"

mkdir -p "${OUT_DIR}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SUMMARY_JSON="${OUT_DIR}/${STAMP}-bl31-ui-ecs-rollout.json"

aws_ecs_service_query() {
  local service="$1"
  local query="$2"
  aws ecs describe-services \
    --region "${AWS_REGION}" \
    --cluster "${ECS_CLUSTER}" \
    --services "${service}" \
    --query "services[0].${query}" \
    --output text
}

resolve_public_ip_for_service() {
  local service="$1"
  local task_arn eni_id public_ip private_ip

  task_arn="$(aws ecs list-tasks \
    --region "${AWS_REGION}" \
    --cluster "${ECS_CLUSTER}" \
    --service-name "${service}" \
    --desired-status RUNNING \
    --query 'taskArns[0]' \
    --output text)"

  if [[ -z "${task_arn}" || "${task_arn}" == "None" ]]; then
    return 1
  fi

  eni_id="$(aws ecs describe-tasks \
    --region "${AWS_REGION}" \
    --cluster "${ECS_CLUSTER}" \
    --tasks "${task_arn}" \
    --query "tasks[0].attachments[0].details[?name=='networkInterfaceId'].value | [0]" \
    --output text)"

  if [[ -z "${eni_id}" || "${eni_id}" == "None" ]]; then
    return 1
  fi

  public_ip="$(aws ec2 describe-network-interfaces \
    --region "${AWS_REGION}" \
    --network-interface-ids "${eni_id}" \
    --query 'NetworkInterfaces[0].Association.PublicIp' \
    --output text)"

  if [[ -n "${public_ip}" && "${public_ip}" != "None" ]]; then
    printf '%s\n' "${public_ip}"
    return 0
  fi

  private_ip="$(aws ec2 describe-network-interfaces \
    --region "${AWS_REGION}" \
    --network-interface-ids "${eni_id}" \
    --query 'NetworkInterfaces[0].PrivateIpAddress' \
    --output text)"

  if [[ -n "${private_ip}" && "${private_ip}" != "None" ]]; then
    printf '%s\n' "${private_ip}"
    return 0
  fi

  return 1
}

http_probe() {
  local url="$1"
  local out_file="$2"

  set +e
  curl -fsS --max-time 20 "${url}" >"${out_file}" 2>"${out_file}.err"
  local rc=$?
  set -e

  return ${rc}
}

ensure_log_group_exists_for_taskdef() {
  local taskdef="$1"
  local log_group

  log_group="$(aws ecs describe-task-definition \
    --region "${AWS_REGION}" \
    --task-definition "${taskdef}" \
    --query 'taskDefinition.containerDefinitions[0].logConfiguration.options."awslogs-group"' \
    --output text)"

  if [[ -z "${log_group}" || "${log_group}" == "None" ]]; then
    return 0
  fi

  if ! aws logs describe-log-groups \
    --region "${AWS_REGION}" \
    --log-group-name-prefix "${log_group}" \
    --query 'logGroups[?logGroupName==`'"${log_group}"'`].logGroupName' \
    --output text | grep -qx "${log_group}"; then
    aws logs create-log-group --region "${AWS_REGION}" --log-group-name "${log_group}"
    echo "  - Created missing log group: ${log_group}"
  else
    echo "  - Log group present: ${log_group}"
  fi
}

echo "[1/8] Resolve target task definition"
TARGET_TASKDEF="${TARGET_TASKDEF:-}"
if [[ -z "${TARGET_TASKDEF}" ]]; then
  TARGET_TASKDEF="$(aws ecs list-task-definitions \
    --region "${AWS_REGION}" \
    --family-prefix "${UI_TASKDEF_FAMILY}" \
    --status ACTIVE \
    --sort DESC \
    --max-items 1 \
    --query 'taskDefinitionArns[0]' \
    --output text)"
fi

if [[ -z "${TARGET_TASKDEF}" || "${TARGET_TASKDEF}" == "None" ]]; then
  echo "ERROR: could not resolve TARGET_TASKDEF for family ${UI_TASKDEF_FAMILY}" >&2
  exit 10
fi

echo "  - TARGET_TASKDEF=${TARGET_TASKDEF}"

UI_TASKDEF_BEFORE="$(aws_ecs_service_query "${UI_SERVICE}" 'taskDefinition')"
API_TASKDEF_BEFORE="$(aws_ecs_service_query "${API_SERVICE}" 'taskDefinition')"

if [[ -z "${UI_TASKDEF_BEFORE}" || "${UI_TASKDEF_BEFORE}" == "None" ]]; then
  echo "ERROR: UI service ${UI_SERVICE} not found in cluster ${ECS_CLUSTER}" >&2
  exit 11
fi
if [[ -z "${API_TASKDEF_BEFORE}" || "${API_TASKDEF_BEFORE}" == "None" ]]; then
  echo "ERROR: API service ${API_SERVICE} not found in cluster ${ECS_CLUSTER}" >&2
  exit 11
fi

echo "[2/8] Ensure UI log group exists for target task definition"
ensure_log_group_exists_for_taskdef "${TARGET_TASKDEF}"

echo "[3/8] Update UI service"
UPDATE_ARGS=(
  ecs update-service
  --region "${AWS_REGION}"
  --cluster "${ECS_CLUSTER}"
  --service "${UI_SERVICE}"
  --task-definition "${TARGET_TASKDEF}"
)
if [[ "${FORCE_NEW_DEPLOYMENT}" == "1" ]]; then
  UPDATE_ARGS+=(--force-new-deployment)
fi
aws "${UPDATE_ARGS[@]}" >/dev/null

echo "[4/8] Wait for services-stable (${UI_SERVICE})"
aws ecs wait services-stable \
  --region "${AWS_REGION}" \
  --cluster "${ECS_CLUSTER}" \
  --services "${UI_SERVICE}"

echo "[5/8] Collect ECS status"
UI_TASKDEF_AFTER="$(aws_ecs_service_query "${UI_SERVICE}" 'taskDefinition')"
UI_RUNNING_AFTER="$(aws_ecs_service_query "${UI_SERVICE}" 'runningCount')"
UI_DESIRED_AFTER="$(aws_ecs_service_query "${UI_SERVICE}" 'desiredCount')"
UI_STATUS_AFTER="$(aws_ecs_service_query "${UI_SERVICE}" 'status')"
API_TASKDEF_AFTER="$(aws_ecs_service_query "${API_SERVICE}" 'taskDefinition')"
API_RUNNING_AFTER="$(aws_ecs_service_query "${API_SERVICE}" 'runningCount')"
API_DESIRED_AFTER="$(aws_ecs_service_query "${API_SERVICE}" 'desiredCount')"

if [[ "${UI_RUNNING_AFTER}" == "None" || "${UI_RUNNING_AFTER}" -lt 1 ]]; then
  echo "ERROR: UI service has no running task after rollout (running=${UI_RUNNING_AFTER})" >&2
  exit 20
fi
if [[ "${API_RUNNING_AFTER}" == "None" || "${API_RUNNING_AFTER}" -lt 1 ]]; then
  echo "ERROR: API service has no running task after UI rollout (running=${API_RUNNING_AFTER})" >&2
  exit 21
fi

echo "[6/8] Probe UI /healthz"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

UI_IP="$(resolve_public_ip_for_service "${UI_SERVICE}" || true)"
if [[ -z "${UI_IP}" ]]; then
  echo "ERROR: failed to resolve running task IP for ${UI_SERVICE}" >&2
  exit 22
fi
UI_URL="http://${UI_IP}:${UI_CONTAINER_PORT}${UI_HEALTH_PATH}"
UI_BODY_FILE="${TMP_DIR}/ui-health.out"
if ! http_probe "${UI_URL}" "${UI_BODY_FILE}"; then
  echo "ERROR: UI health probe failed (${UI_URL})" >&2
  cat "${UI_BODY_FILE}.err" >&2 || true
  exit 23
fi

echo "[7/8] Probe API /health"
API_IP="$(resolve_public_ip_for_service "${API_SERVICE}" || true)"
if [[ -z "${API_IP}" ]]; then
  echo "ERROR: failed to resolve running task IP for ${API_SERVICE}" >&2
  exit 24
fi
API_URL="http://${API_IP}:${API_CONTAINER_PORT}${API_HEALTH_PATH}"
API_BODY_FILE="${TMP_DIR}/api-health.out"
if ! http_probe "${API_URL}" "${API_BODY_FILE}"; then
  echo "ERROR: API health probe failed (${API_URL})" >&2
  cat "${API_BODY_FILE}.err" >&2 || true
  exit 25
fi

echo "[8/8] Write evidence summary"
UI_EVENTS_JSON="$(aws ecs describe-services \
  --region "${AWS_REGION}" \
  --cluster "${ECS_CLUSTER}" \
  --services "${UI_SERVICE}" \
  --query 'services[0].events[0:5].[createdAt,message]' \
  --output json)"

python3 - <<'PY' \
  "${SUMMARY_JSON}" \
  "${STAMP}" \
  "${AWS_REGION}" \
  "${ECS_CLUSTER}" \
  "${UI_SERVICE}" \
  "${UI_TASKDEF_BEFORE}" \
  "${UI_TASKDEF_AFTER}" \
  "${UI_STATUS_AFTER}" \
  "${UI_DESIRED_AFTER}" \
  "${UI_RUNNING_AFTER}" \
  "${UI_IP}" \
  "${UI_URL}" \
  "${UI_BODY_FILE}" \
  "${API_SERVICE}" \
  "${API_TASKDEF_BEFORE}" \
  "${API_TASKDEF_AFTER}" \
  "${API_DESIRED_AFTER}" \
  "${API_RUNNING_AFTER}" \
  "${API_IP}" \
  "${API_URL}" \
  "${API_BODY_FILE}" \
  "${UI_EVENTS_JSON}"
import json
import pathlib
import sys

(
    out,
    stamp,
    region,
    cluster,
    ui_service,
    ui_taskdef_before,
    ui_taskdef_after,
    ui_status_after,
    ui_desired_after,
    ui_running_after,
    ui_ip,
    ui_url,
    ui_body_file,
    api_service,
    api_taskdef_before,
    api_taskdef_after,
    api_desired_after,
    api_running_after,
    api_ip,
    api_url,
    api_body_file,
    ui_events_json,
) = sys.argv[1:]

payload = {
    "timestampUtc": stamp,
    "environment": "dev",
    "region": region,
    "cluster": cluster,
    "uiService": {
        "name": ui_service,
        "taskDefinitionBefore": ui_taskdef_before,
        "taskDefinitionAfter": ui_taskdef_after,
        "statusAfter": ui_status_after,
        "desiredCountAfter": int(ui_desired_after),
        "runningCountAfter": int(ui_running_after),
        "taskIp": ui_ip,
        "healthUrl": ui_url,
        "healthResponse": pathlib.Path(ui_body_file).read_text(encoding="utf-8").strip(),
        "recentEvents": json.loads(ui_events_json),
    },
    "apiService": {
        "name": api_service,
        "taskDefinitionBefore": api_taskdef_before,
        "taskDefinitionAfter": api_taskdef_after,
        "desiredCountAfter": int(api_desired_after),
        "runningCountAfter": int(api_running_after),
        "taskIp": api_ip,
        "healthUrl": api_url,
        "healthResponse": pathlib.Path(api_body_file).read_text(encoding="utf-8").strip(),
    },
    "rollbackHint": {
        "uiService": ui_service,
        "rollbackTaskDefinition": ui_taskdef_before,
    },
}

path = pathlib.Path(out)
path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(path)
PY

echo "Done. Evidence: ${SUMMARY_JSON}"