#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

legacy_caller=0
runtime_ref=0

LEGACY_USER="swisstopo-api-deploy"
REF_REGEX='swisstopo-api-deploy|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|aws_access_key_id|aws_secret_access_key|AKIA[0-9A-Z]{16}'

short_key() {
  local key="$1"
  local len=${#key}
  if (( len <= 8 )); then
    printf '%s' '***'
    return
  fi
  printf '%s***%s' "${key:0:4}" "${key: -4}"
}

print_file_list_hits() {
  local title="$1"
  shift
  local -a files=("$@")

  echo "--- ${title} ---"
  if [[ ${#files[@]} -eq 0 ]]; then
    echo "(keine prüfbaren Dateien gefunden)"
    return
  fi

  local hits
  hits="$(grep -HnE "$REF_REGEX" "${files[@]}" 2>/dev/null || true)"
  if [[ -z "$hits" ]]; then
    echo "(keine Treffer)"
    return
  fi

  runtime_ref=1
  echo "$hits" \
    | sed -E 's/(AWS_ACCESS_KEY_ID=).*/\1<redacted>/g' \
    | sed -E 's/(AWS_SECRET_ACCESS_KEY=).*/\1<redacted>/g' \
    | sed -E 's/(aws_access_key_id\s*=).*/\1 <redacted>/gI' \
    | sed -E 's/(aws_secret_access_key\s*=).*/\1 <redacted>/gI' \
    | awk -F: '{print $1 ":" $2 " (match)"}'
}

print_dir_file_hits() {
  local title="$1"
  shift
  local -a dirs=("$@")

  echo "--- ${title} ---"
  if [[ ${#dirs[@]} -eq 0 ]]; then
    echo "(keine prüfbaren Pfade gefunden)"
    return
  fi

  local hits
  hits="$(grep -RIlE "$REF_REGEX" --include='*.service' --include='*.timer' --include='*.conf' --include='*.env' --include='*.sh' -- "${dirs[@]}" 2>/dev/null || true)"
  if [[ -z "$hits" ]]; then
    echo "(keine Treffer)"
    return
  fi

  runtime_ref=1
  echo "$hits"
}

echo "=== Legacy Runtime Consumer Audit (read-only) ==="
echo "Repo: $ROOT_DIR"
echo

if command -v aws >/dev/null 2>&1; then
  caller_arn="$(aws sts get-caller-identity --query 'Arn' --output text 2>/dev/null || true)"
  account_id="$(aws sts get-caller-identity --query 'Account' --output text 2>/dev/null || true)"
  if [[ -n "$caller_arn" && "$caller_arn" != "None" ]]; then
    echo "Caller ARN: ${caller_arn}"
    echo "Account:    ${account_id:-unknown}"
    if [[ "$caller_arn" == *":user/${LEGACY_USER}" ]]; then
      legacy_caller=1
      echo "WARN: Aktiver AWS-Caller ist Legacy-IAM-User ${LEGACY_USER}."
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
echo "--- Runtime-Environment (sanitisiert) ---"
for var in AWS_PROFILE AWS_DEFAULT_PROFILE AWS_REGION AWS_DEFAULT_REGION AWS_ROLE_ARN AWS_WEB_IDENTITY_TOKEN_FILE; do
  if [[ -n "${!var-}" ]]; then
    echo "${var}=set"
  fi
done

if [[ -n "${AWS_ACCESS_KEY_ID-}" ]]; then
  echo "AWS_ACCESS_KEY_ID=$(short_key "$AWS_ACCESS_KEY_ID")"
  runtime_ref=1
fi
if [[ -n "${AWS_SECRET_ACCESS_KEY-}" ]]; then
  echo "AWS_SECRET_ACCESS_KEY=set"
  runtime_ref=1
fi
if [[ -n "${AWS_SESSION_TOKEN-}" ]]; then
  echo "AWS_SESSION_TOKEN=set"
fi

echo
profile_files=(
  "$HOME/.bashrc"
  "$HOME/.bash_profile"
  "$HOME/.profile"
  "$HOME/.zshrc"
  "$HOME/.zprofile"
  "$HOME/.config/fish/config.fish"
  "/etc/environment"
)
existing_profiles=()
for f in "${profile_files[@]}"; do
  [[ -f "$f" ]] && existing_profiles+=("$f")
done
print_file_list_hits "Shell-/Environment-Profile" "${existing_profiles[@]}"

echo
aws_config_files=("$HOME/.aws/credentials" "$HOME/.aws/config")
existing_aws_config=()
for f in "${aws_config_files[@]}"; do
  [[ -f "$f" ]] && existing_aws_config+=("$f")
done
print_file_list_hits "AWS Credential/Config Files" "${existing_aws_config[@]}"

echo
if command -v crontab >/dev/null 2>&1; then
  tmp_cron="$(mktemp)"
  if crontab -l >"$tmp_cron" 2>/dev/null; then
    if grep -qE "$REF_REGEX" "$tmp_cron"; then
      runtime_ref=1
      echo "--- User-Crontab ---"
      echo "Treffer in user crontab gefunden (Inhalt redacted)."
    else
      echo "--- User-Crontab ---"
      echo "(keine Treffer)"
    fi
  else
    echo "--- User-Crontab ---"
    echo "(keine user crontab oder nicht lesbar)"
  fi
  rm -f "$tmp_cron"
else
  echo "--- User-Crontab ---"
  echo "(crontab nicht verfügbar)"
fi

echo
system_cron_paths=("/etc/cron.d" "/etc/cron.daily" "/etc/cron.hourly" "/etc/cron.weekly" "/etc/cron.monthly")
existing_system_cron=()
for p in "${system_cron_paths[@]}"; do
  [[ -d "$p" ]] && existing_system_cron+=("$p")
done
print_dir_file_hits "System-Cron" "${existing_system_cron[@]}"

echo
systemd_paths=("$HOME/.config/systemd/user" "/etc/systemd/system")
existing_systemd=()
for p in "${systemd_paths[@]}"; do
  [[ -d "$p" ]] && existing_systemd+=("$p")
done
print_dir_file_hits "Systemd Units" "${existing_systemd[@]}"

echo
openclaw_config_files=(
  "/data/.openclaw/openclaw.json"
  "/data/.openclaw/openclaw.json.bak"
  "/data/.openclaw/cron/jobs.json"
  "/data/.openclaw/cron/jobs.json.bak"
)
existing_openclaw_cfg=()
for f in "${openclaw_config_files[@]}"; do
  [[ -f "$f" ]] && existing_openclaw_cfg+=("$f")
done
print_file_list_hits "OpenClaw Config-Dateien" "${existing_openclaw_cfg[@]}"

echo
echo "Exit-Code-Interpretation:"
echo "  0  = kein harter Befund"
echo " 10  = Legacy-IAM-User aktuell als Caller erkannt"
echo " 20  = Runtime-Referenzen auf Legacy-Key/Principal gefunden"
echo " 30  = 10 + 20 (beides)"

exit_code=0
if (( legacy_caller == 1 )); then
  ((exit_code+=10))
fi
if (( runtime_ref == 1 )); then
  ((exit_code+=20))
fi

exit "$exit_code"
