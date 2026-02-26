#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

status=0

echo "=== BL-17 Posture Check: OIDC-first + AssumeRole-first ==="
echo "Repo: $ROOT_DIR"
echo

echo "--- 1) Workflow-Check (OIDC required) ---"
if ls .github/workflows/*.yml >/dev/null 2>&1; then
  if grep -RIn "configure-aws-credentials" .github/workflows >/dev/null 2>&1; then
    echo "OK: configure-aws-credentials in Workflows gefunden."
  else
    echo "WARN: Kein configure-aws-credentials in .github/workflows gefunden."
    status=10
  fi

  if grep -RInE "id-token:\s*write|id-token: write" .github/workflows >/dev/null 2>&1; then
    echo "OK: id-token: write in Workflows gefunden."
  else
    echo "WARN: Kein id-token: write in .github/workflows gefunden."
    status=10
  fi

  key_refs=$(grep -RInE "aws-access-key-id|aws-secret-access-key|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY" .github/workflows || true)
  if [[ -n "$key_refs" ]]; then
    echo "WARN: Statische AWS-Key-Referenzen in Workflows gefunden:"
    echo "$key_refs"
    status=20
  else
    echo "OK: Keine statischen AWS-Key-Referenzen in Workflows."
  fi
else
  echo "WARN: Keine Workflow-Dateien gefunden."
  status=10
fi

echo
echo "--- 2) Runtime-Caller (AssumeRole-first) ---"
if command -v aws >/dev/null 2>&1; then
  if caller_arn=$(aws sts get-caller-identity --query 'Arn' --output text 2>/dev/null); then
    echo "Caller ARN: $caller_arn"
    if [[ "$caller_arn" == *":assumed-role/openclaw-ops-role/"* ]]; then
      echo "OK: Caller läuft über openclaw-ops-role (AssumeRole)."
    elif [[ "$caller_arn" == *":user/swisstopo-api-deploy" ]]; then
      echo "WARN: Caller ist Legacy-IAM-User (nur Fallback erlaubt)."
      status=30
    else
      echo "INFO: Caller ist weder Legacy-User noch openclaw-ops-role (prüfen, ob Kontext erwartet ist)."
    fi
  else
    echo "INFO: Kein gültiger AWS-Caller im aktuellen Environment (oder keine Credentials gesetzt)."
  fi
else
  echo "INFO: aws CLI nicht gefunden — Caller-Check übersprungen."
fi

echo
echo "--- 3) Kontext-Checks (read-only Audits) ---"
if [[ -x ./scripts/audit_legacy_aws_consumer_refs.sh ]]; then
  set +e
  ./scripts/audit_legacy_aws_consumer_refs.sh >/tmp/bl17_audit_repo.log 2>&1
  repo_audit_rc=$?
  set -e
  echo "audit_legacy_aws_consumer_refs.sh => Exit $repo_audit_rc"
  if (( repo_audit_rc != 0 )); then
    echo "INFO: Details siehe /tmp/bl17_audit_repo.log"
  fi
else
  echo "INFO: ./scripts/audit_legacy_aws_consumer_refs.sh nicht ausführbar/gefunden."
fi

if [[ -x ./scripts/audit_legacy_runtime_consumers.sh ]]; then
  set +e
  ./scripts/audit_legacy_runtime_consumers.sh >/tmp/bl17_audit_runtime.log 2>&1
  runtime_audit_rc=$?
  set -e
  echo "audit_legacy_runtime_consumers.sh => Exit $runtime_audit_rc"
  if (( runtime_audit_rc != 0 )); then
    echo "INFO: Details siehe /tmp/bl17_audit_runtime.log"
  fi
else
  echo "INFO: ./scripts/audit_legacy_runtime_consumers.sh nicht ausführbar/gefunden."
fi

echo
echo "Exit-Code-Interpretation:"
echo "  0  = OIDC-/AssumeRole-Posture ohne harte Befunde"
echo " 10  = OIDC-Marker in Workflows fehlen"
echo " 20  = statische AWS-Key-Referenzen in Workflows gefunden"
echo " 30  = aktiver Caller ist Legacy-IAM-User"

exit "$status"
