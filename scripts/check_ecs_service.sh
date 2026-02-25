#!/usr/bin/env bash
set -euo pipefail

AWS_REGION="${AWS_REGION:-eu-central-1}"
ECS_CLUSTER="${ECS_CLUSTER:-swisstopo-dev}"
ECS_SERVICE="${ECS_SERVICE:-swisstopo-dev-api}"
EVENT_LIMIT="${EVENT_LIMIT:-15}"

if ! command -v aws >/dev/null 2>&1; then
  echo "Fehler: aws CLI nicht gefunden." >&2
  exit 1
fi

echo "== ECS Service Status =="
echo "Region:  ${AWS_REGION}"
echo "Cluster: ${ECS_CLUSTER}"
echo "Service: ${ECS_SERVICE}"
echo

aws ecs describe-services \
  --region "${AWS_REGION}" \
  --cluster "${ECS_CLUSTER}" \
  --services "${ECS_SERVICE}" \
  --query 'services[0].{status:status,desired:desiredCount,running:runningCount,pending:pendingCount,taskDefinition:taskDefinition,rolloutState:deployments[0].rolloutState,rolloutReason:deployments[0].rolloutStateReason}' \
  --output table

echo
echo "== Letzte ${EVENT_LIMIT} Service-Events =="
aws ecs describe-services \
  --region "${AWS_REGION}" \
  --cluster "${ECS_CLUSTER}" \
  --services "${ECS_SERVICE}" \
  --query "services[0].events[0:${EVENT_LIMIT}].[createdAt,message]" \
  --output table

echo
echo "== Laufende Tasks =="
TASKS=$(aws ecs list-tasks \
  --region "${AWS_REGION}" \
  --cluster "${ECS_CLUSTER}" \
  --service-name "${ECS_SERVICE}" \
  --query 'taskArns' \
  --output text)

if [[ -z "${TASKS}" || "${TASKS}" == "None" ]]; then
  echo "Keine laufenden Tasks gefunden."
  exit 0
fi

aws ecs describe-tasks \
  --region "${AWS_REGION}" \
  --cluster "${ECS_CLUSTER}" \
  --tasks ${TASKS} \
  --query 'tasks[].{taskArn:taskArn,lastStatus:lastStatus,healthStatus:healthStatus,startedAt:startedAt,stoppedReason:stoppedReason,containers:containers[].{name:name,lastStatus:lastStatus,exitCode:exitCode,reason:reason}}' \
  --output json
