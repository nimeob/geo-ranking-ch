#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

status=0

echo "=== Legacy AWS Consumer Audit (read-only) ==="
echo "Repo: $ROOT_DIR"
echo

if command -v aws >/dev/null 2>&1; then
  if caller_arn=$(aws sts get-caller-identity --query 'Arn' --output text 2>/dev/null); then
    account_id=$(aws sts get-caller-identity --query 'Account' --output text 2>/dev/null || true)
    echo "Caller ARN: ${caller_arn}"
    echo "Account:    ${account_id:-unknown}"

    if [[ "$caller_arn" == *":user/swisstopo-api-deploy" ]]; then
      echo "WARN: Aktiver AWS-Caller ist Legacy-IAM-User swisstopo-api-deploy."
      status=10
    else
      echo "OK: Aktiver AWS-Caller ist nicht der Legacy-IAM-User."
    fi
  else
    echo "INFO: Kein gültiger AWS-Caller im aktuellen Environment (oder keine Credentials gesetzt)."
  fi
else
  echo "INFO: aws CLI nicht gefunden — Caller-Check übersprungen."
fi

echo
echo "--- 1) Aktive Workflows: OIDC vs. statische Keys ---"
if ls .github/workflows/*.yml >/dev/null 2>&1; then
  echo "OIDC-Hinweise (configure-aws-credentials):"
  grep -RIn "configure-aws-credentials" .github/workflows || true
  echo
  echo "Statische Key-Hinweise (sollten in aktiven Workflows nicht vorkommen):"
  key_refs=$(grep -RInE "aws-access-key-id|aws-secret-access-key|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY" .github/workflows || true)
  if [[ -n "$key_refs" ]]; then
    echo "$key_refs"
    status=20
  else
    echo "(keine Treffer)"
  fi
else
  echo "(keine Workflow-Dateien gefunden)"
fi

echo
echo "--- 2) Legacy-/Key-Referenzen im Repo (inkl. Doku/Template) ---"
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -c color.ui=never grep -nE "swisstopo-api-deploy|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY" \
    -- . \
    ':(exclude)artifacts/**' \
    ':(exclude).venv/**' \
    ':(exclude).terraform/**' || true
else
  grep -RInE "swisstopo-api-deploy|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY" \
    --exclude-dir=.git \
    --exclude-dir=artifacts \
    --exclude-dir=.venv \
    --exclude-dir=.terraform \
    . || true
fi

echo
echo "--- 3) Skripte mit AWS-CLI-Aufrufen (potenzielle Consumer) ---"
grep -RIl "\baws\b" scripts/*.sh 2>/dev/null || true

echo
echo "Exit-Code-Interpretation:"
echo "  0  = kein harter Befund"
echo " 10  = Legacy-IAM-User aktuell als Caller erkannt"
echo " 20  = statische AWS-Key-Referenz in aktivem Workflow gefunden"

exit "$status"
