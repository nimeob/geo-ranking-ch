#!/usr/bin/env bash
set -euo pipefail

trim() {
  python3 - "$1" <<'PY'
import sys
print(sys.argv[1].strip())
PY
}

RUN_ID="$(trim "${DEV_UI_SMOKE_RUN_ID:-${GITHUB_RUN_ID:-}}")"
if [[ -z "${RUN_ID}" ]]; then
  RUN_ID="$(date +%s)"
fi

USERNAME="$(trim "${DEV_UI_SMOKE_USERNAME:-}")"
PASSWORD="$(trim "${DEV_UI_SMOKE_PASSWORD:-}")"

MISSING=()
if [[ -z "${USERNAME}" ]]; then
  MISSING+=("DEV_UI_SMOKE_USERNAME")
fi
if [[ -z "${PASSWORD}" ]]; then
  MISSING+=("DEV_UI_SMOKE_PASSWORD")
fi

if (( ${#MISSING[@]} > 0 )); then
  mkdir -p reports/evidence
  OUT="reports/evidence/dev-ui-auth-analyze-smoke-blocked-${RUN_ID}.json"

  python3 - "${OUT}" "${RUN_ID}" "${MISSING[@]}" <<'PY'
import json
import pathlib
import sys

out = pathlib.Path(sys.argv[1])
run_id = sys.argv[2]
missing = sys.argv[3:]
required = ["DEV_UI_SMOKE_USERNAME", "DEV_UI_SMOKE_PASSWORD"]

payload = {
    "ok": False,
    "blocked": True,
    "reason": "missing_required_github_secrets",
    "run_id": run_id,
    "required": required,
    "missing": missing,
    "next_step": "Set both repository secrets and re-run gui-dev-live-auth-analyze-smoke workflow.",
}
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

  echo "::error::Missing required secrets for real UI login smoke: ${MISSING[*]}" >&2
  echo "[gui-live-smoke-preflight] blocker_evidence=${OUT}" >&2
  exit 1
fi

echo "[gui-live-smoke-preflight] required secrets present"
