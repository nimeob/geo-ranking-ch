#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: check_bl17_oidc_assumerole_posture.sh [--report-json <path>]

Optional:
  --report-json <path>         Write structured evidence report JSON
  BL17_POSTURE_REPORT_JSON     Alternative env-based report path
USAGE
}

report_json_path="${BL17_POSTURE_REPORT_JSON:-}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --report-json)
      if [[ $# -lt 2 || -z "${2:-}" ]]; then
        echo "ERROR: --report-json requires a file path" >&2
        usage >&2
        exit 2
      fi
      report_json_path="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

status=0
set_status_if_higher() {
  local code="${1:?code required}"
  if (( code > status )); then
    status="$code"
  fi
}

timestamp_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
workflow_check_exit=0
caller_check_exit=0
repo_audit_rc=""
runtime_audit_rc=""

workflow_files_found=true
configure_aws_credentials_found=true
id_token_write_found=true
static_key_refs_found=false

caller_arn=""
caller_classification="not_checked"

echo "=== BL-17 Posture Check: OIDC-first + AssumeRole-first ==="
echo "Repo: $ROOT_DIR"
echo

echo "--- 1) Workflow-Check (OIDC required) ---"
if ls .github/workflows/*.yml >/dev/null 2>&1; then
  if grep -RIn "configure-aws-credentials" .github/workflows >/dev/null 2>&1; then
    echo "OK: configure-aws-credentials in Workflows gefunden."
  else
    echo "WARN: Kein configure-aws-credentials in .github/workflows gefunden."
    configure_aws_credentials_found=false
    workflow_check_exit=10
    set_status_if_higher 10
  fi

  if grep -RInE "id-token:\s*write|id-token: write" .github/workflows >/dev/null 2>&1; then
    echo "OK: id-token: write in Workflows gefunden."
  else
    echo "WARN: Kein id-token: write in .github/workflows gefunden."
    id_token_write_found=false
    workflow_check_exit=10
    set_status_if_higher 10
  fi

  key_refs=$(grep -RInE "aws-access-key-id|aws-secret-access-key|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY" .github/workflows || true)
  if [[ -n "$key_refs" ]]; then
    echo "WARN: Statische AWS-Key-Referenzen in Workflows gefunden:"
    echo "$key_refs"
    static_key_refs_found=true
    workflow_check_exit=20
    set_status_if_higher 20
  else
    echo "OK: Keine statischen AWS-Key-Referenzen in Workflows."
  fi
else
  echo "WARN: Keine Workflow-Dateien gefunden."
  workflow_files_found=false
  configure_aws_credentials_found=false
  id_token_write_found=false
  workflow_check_exit=10
  set_status_if_higher 10
fi

echo
echo "--- 2) Runtime-Caller (AssumeRole-first) ---"
if command -v aws >/dev/null 2>&1; then
  if caller_arn=$(aws sts get-caller-identity --query 'Arn' --output text 2>/dev/null); then
    echo "Caller ARN: $caller_arn"
    if [[ "$caller_arn" == *":assumed-role/openclaw-ops-role/"* ]]; then
      caller_classification="assume-role-openclaw-ops-role"
      echo "OK: Caller läuft über openclaw-ops-role (AssumeRole)."
    elif [[ "$caller_arn" == *":user/swisstopo-api-deploy" ]]; then
      caller_classification="legacy-user-swisstopo-api-deploy"
      caller_check_exit=30
      echo "WARN: Caller ist Legacy-IAM-User (nur Fallback erlaubt)."
      set_status_if_higher 30
    else
      caller_classification="other-principal"
      echo "INFO: Caller ist weder Legacy-User noch openclaw-ops-role (prüfen, ob Kontext erwartet ist)."
    fi
  else
    caller_classification="aws-cli-available-no-valid-caller"
    echo "INFO: Kein gültiger AWS-Caller im aktuellen Environment (oder keine Credentials gesetzt)."
  fi
else
  caller_classification="aws-cli-missing"
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

if [[ -n "$report_json_path" ]]; then
  export BL17_REPORT_JSON_PATH="$report_json_path"
  export BL17_REPORT_TIMESTAMP_UTC="$timestamp_utc"
  export BL17_REPORT_WORKFLOW_FILES_FOUND="$workflow_files_found"
  export BL17_REPORT_CONFIGURE_AWS_CREDENTIALS_FOUND="$configure_aws_credentials_found"
  export BL17_REPORT_ID_TOKEN_WRITE_FOUND="$id_token_write_found"
  export BL17_REPORT_STATIC_KEY_REFS_FOUND="$static_key_refs_found"
  export BL17_REPORT_CALLER_ARN="$caller_arn"
  export BL17_REPORT_CALLER_CLASSIFICATION="$caller_classification"
  export BL17_REPORT_WORKFLOW_EXIT="$workflow_check_exit"
  export BL17_REPORT_CALLER_EXIT="$caller_check_exit"
  export BL17_REPORT_REPO_AUDIT_RC="$repo_audit_rc"
  export BL17_REPORT_RUNTIME_AUDIT_RC="$runtime_audit_rc"
  export BL17_REPORT_FINAL_EXIT="$status"

  python3 - <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path


def env_bool(name: str) -> bool:
    return os.environ[name].lower() == "true"


def env_int_or_none(name: str) -> int | None:
    raw = os.environ.get(name, "")
    if raw == "":
        return None
    return int(raw)


report = {
    "version": 1,
    "generated_at_utc": os.environ["BL17_REPORT_TIMESTAMP_UTC"],
    "caller": {
        "arn": os.environ["BL17_REPORT_CALLER_ARN"] or None,
        "classification": os.environ["BL17_REPORT_CALLER_CLASSIFICATION"],
    },
    "workflow": {
        "workflow_files_found": env_bool("BL17_REPORT_WORKFLOW_FILES_FOUND"),
        "configure_aws_credentials_found": env_bool("BL17_REPORT_CONFIGURE_AWS_CREDENTIALS_FOUND"),
        "id_token_write_found": env_bool("BL17_REPORT_ID_TOKEN_WRITE_FOUND"),
        "static_key_refs_found": env_bool("BL17_REPORT_STATIC_KEY_REFS_FOUND"),
    },
    "exit_codes": {
        "final": int(os.environ["BL17_REPORT_FINAL_EXIT"]),
        "workflow_check": int(os.environ["BL17_REPORT_WORKFLOW_EXIT"]),
        "caller_check": int(os.environ["BL17_REPORT_CALLER_EXIT"]),
        "audit_legacy_aws_consumer_refs": env_int_or_none("BL17_REPORT_REPO_AUDIT_RC"),
        "audit_legacy_runtime_consumers": env_int_or_none("BL17_REPORT_RUNTIME_AUDIT_RC"),
    },
}

report_path = Path(os.environ["BL17_REPORT_JSON_PATH"])
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

  echo "Structured report written: $report_json_path"
fi

echo
echo "Exit-Code-Interpretation:"
echo "  0  = OIDC-/AssumeRole-Posture ohne harte Befunde"
echo " 10  = OIDC-Marker in Workflows fehlen"
echo " 20  = statische AWS-Key-Referenzen in Workflows gefunden"
echo " 30  = aktiver Caller ist Legacy-IAM-User"

exit "$status"
