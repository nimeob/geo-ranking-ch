# Dev-Runbook: Self-Signed TLS + `/analyze` Smoke (inkl. Token-Auth)

## Ziel
Reproduzierbarer lokaler/devnaher HTTPS-Check ohne globales `curl -k`.

## 1) Self-Signed Zertifikat erzeugen

```bash
./scripts/generate_dev_tls_cert.sh
```

Optional mit Zielpfad:

```bash
DEV_TLS_CERT_DIR=/tmp/geo-dev-tls \
DEV_TLS_CERT_BASENAME=geo-dev \
./scripts/generate_dev_tls_cert.sh
```

> Das Script erzeugt `.crt` + `.key` (Key mit `0600`) und schreibt keine Secrets ins Repo.

## 2) Webservice mit TLS starten

```bash
TLS_CERT_FILE=/tmp/geo-ranking-ch-dev-tls/dev-self-signed.crt \
TLS_KEY_FILE=/tmp/geo-ranking-ch-dev-tls/dev-self-signed.key \
API_AUTH_TOKEN=bl18-token \
PORT=8443 \
python -m src.api.web_service
```

Optionaler Redirect-Listener:

```bash
TLS_ENABLE_HTTP_REDIRECT=1 TLS_REDIRECT_HTTP_PORT=8080
```

## 3) HTTPS-Smoke mit CA-Trust + Token

```bash
DEV_BASE_URL="https://localhost:8443" \
DEV_TLS_CA_CERT="/tmp/geo-ranking-ch-dev-tls/dev-self-signed.crt" \
DEV_API_AUTH_TOKEN="bl18-token" \
SMOKE_QUERY="__ok__" \
./scripts/run_remote_api_smoketest.sh
```

Erwartung: `PASS` mit HTTP `200`, `ok=true`, `result` vorhanden.

## 4) Test-/Nachweis-Referenz

- Smoke-Script unterstützt optionales `DEV_TLS_CA_CERT` via `curl --cacert`.
- Automatisierter Nachweis: `tests/test_remote_smoke_script.py::test_smoke_script_passes_against_self_signed_https_with_ca_cert`.
