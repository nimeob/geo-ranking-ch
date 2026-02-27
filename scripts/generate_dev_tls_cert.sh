#!/usr/bin/env bash
set -euo pipefail

# Erzeugt ein self-signed Dev-Zertifikat (inkl. SAN) für lokale HTTPS-Tests.
# Kein Secret wird ins Repo geschrieben (Default-Ziel: /tmp).
#
# Nutzung:
#   ./scripts/generate_dev_tls_cert.sh
#   DEV_TLS_CERT_DIR=/tmp/geo-tls DEV_TLS_CERT_BASENAME=geo-dev ./scripts/generate_dev_tls_cert.sh
#
# Optionale ENV:
#   DEV_TLS_CERT_DIR=/tmp/geo-dev-tls      # Zielordner
#   DEV_TLS_CERT_BASENAME=dev-self-signed  # Dateiname ohne Endung
#   DEV_TLS_CERT_DAYS=14                   # Gültigkeit in Tagen
#   DEV_TLS_CERT_SAN="DNS:localhost,IP:127.0.0.1"  # Subject Alternative Names

if ! command -v openssl >/dev/null 2>&1; then
  echo "[dev-tls] openssl ist nicht installiert oder nicht im PATH." >&2
  exit 2
fi

CERT_DIR="${DEV_TLS_CERT_DIR:-/tmp/geo-ranking-ch-dev-tls}"
CERT_BASENAME="${DEV_TLS_CERT_BASENAME:-dev-self-signed}"
CERT_DAYS="${DEV_TLS_CERT_DAYS:-14}"
CERT_SAN="${DEV_TLS_CERT_SAN:-DNS:localhost,IP:127.0.0.1}"

CERT_DIR="$(python3 - "${CERT_DIR}" <<'PY'
import sys
print(sys.argv[1].strip())
PY
)"
CERT_BASENAME="$(python3 - "${CERT_BASENAME}" <<'PY'
import sys
print(sys.argv[1].strip())
PY
)"
CERT_DAYS="$(python3 - "${CERT_DAYS}" <<'PY'
import sys
print(sys.argv[1].strip())
PY
)"
CERT_SAN="$(python3 - "${CERT_SAN}" <<'PY'
import sys
print(sys.argv[1].strip())
PY
)"

if [[ -z "${CERT_DIR}" || -z "${CERT_BASENAME}" ]]; then
  echo "[dev-tls] DEV_TLS_CERT_DIR und DEV_TLS_CERT_BASENAME dürfen nicht leer sein." >&2
  exit 2
fi

if [[ ! "${CERT_DAYS}" =~ ^[0-9]+$ ]] || [[ "${CERT_DAYS}" -le 0 ]]; then
  echo "[dev-tls] DEV_TLS_CERT_DAYS muss eine Ganzzahl > 0 sein (aktuell: ${CERT_DAYS})." >&2
  exit 2
fi

if [[ -z "${CERT_SAN}" ]]; then
  echo "[dev-tls] DEV_TLS_CERT_SAN darf nicht leer sein." >&2
  exit 2
fi

mkdir -p "${CERT_DIR}"
CERT_PATH="${CERT_DIR}/${CERT_BASENAME}.crt"
KEY_PATH="${CERT_DIR}/${CERT_BASENAME}.key"

TMP_OPENSSL_CONF="$(mktemp)"
trap 'rm -f "${TMP_OPENSSL_CONF}"' EXIT

cat >"${TMP_OPENSSL_CONF}" <<EOF
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = localhost

[v3_req]
subjectAltName = ${CERT_SAN}
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
EOF

openssl req -x509 -newkey rsa:2048 -nodes \
  -days "${CERT_DAYS}" \
  -keyout "${KEY_PATH}" \
  -out "${CERT_PATH}" \
  -config "${TMP_OPENSSL_CONF}" \
  >/dev/null 2>&1

chmod 600 "${KEY_PATH}"

cat <<EOF
[dev-tls] Zertifikat erstellt.

CERT: ${CERT_PATH}
KEY:  ${KEY_PATH}

Beispielstart Webservice (HTTPS):
TLS_CERT_FILE="${CERT_PATH}" \\
TLS_KEY_FILE="${KEY_PATH}" \\
PORT=8443 \\
python -m src.web_service

Beispiel-Smoke mit Trust-Anchor + Token:
DEV_BASE_URL="https://localhost:8443" \\
DEV_TLS_CA_CERT="${CERT_PATH}" \\
DEV_API_AUTH_TOKEN="<token>" \\
./scripts/run_remote_api_smoketest.sh
EOF
