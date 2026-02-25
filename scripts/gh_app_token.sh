#!/usr/bin/env bash
set -euo pipefail

: "${GITHUB_APP_ID:?GITHUB_APP_ID is required}"
: "${GITHUB_APP_INSTALLATION_ID:?GITHUB_APP_INSTALLATION_ID is required}"
: "${GITHUB_APP_PRIVATE_KEY_PATH:?GITHUB_APP_PRIVATE_KEY_PATH is required}"

if [[ ! -f "$GITHUB_APP_PRIVATE_KEY_PATH" ]]; then
  echo "Private key not found at: $GITHUB_APP_PRIVATE_KEY_PATH" >&2
  exit 1
fi

b64url() {
  openssl base64 -A | tr '+/' '-_' | tr -d '='
}

now=$(date +%s)
iat=$((now-60))
exp=$((now+540))

header='{"alg":"RS256","typ":"JWT"}'
payload=$(printf '{"iat":%s,"exp":%s,"iss":"%s"}' "$iat" "$exp" "$GITHUB_APP_ID")

header_b64=$(printf '%s' "$header" | b64url)
payload_b64=$(printf '%s' "$payload" | b64url)
unsigned="${header_b64}.${payload_b64}"

signature_b64=$(printf '%s' "$unsigned" | openssl dgst -sha256 -sign "$GITHUB_APP_PRIVATE_KEY_PATH" -binary | b64url)
jwt="${unsigned}.${signature_b64}"

resp=$(curl -fsSL -X POST \
  -H "Authorization: Bearer ${jwt}" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/app/installations/${GITHUB_APP_INSTALLATION_ID}/access_tokens")

token=$(printf '%s' "$resp" | python3 -c 'import sys,json; print(json.load(sys.stdin)["token"])')

if [[ -z "$token" ]]; then
  echo "Failed to mint installation token" >&2
  exit 1
fi

printf '%s\n' "$token"
