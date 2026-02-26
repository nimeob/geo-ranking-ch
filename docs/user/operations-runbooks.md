# Operations Quick Guide (BL-19.6)

Dieser Guide ist für den **Tagesbetrieb** gedacht: schnelle Health-Checks, reproduzierbare Smoke-/Stability-Läufe und ein klarer Incident-Pfad.

> Für tiefe AWS-/Infra-Details siehe: [`../OPERATIONS.md`](../OPERATIONS.md) und [`../DEPLOYMENT_AWS.md`](../DEPLOYMENT_AWS.md).

## 1) Daily Quick Check (2–5 Minuten)

### A) Service erreichbar?

```bash
curl -fsS "${SERVICE_HEALTH_URL:-http://localhost:8080/health}"
```

Erwartung: HTTP `200` und JSON mit `ok: true`.

### B) Lokaler API-Basischeck

```bash
./scripts/run_webservice_e2e.sh
```

Erwartung: Exit `0`.

### C) Optional: Dev-Check gegen Remote-Endpoint

```bash
DEV_BASE_URL="https://<dein-dev-endpoint>" ./scripts/run_webservice_e2e.sh
```

---

## 2) Reproduzierbarer Smoke-Test (`/analyze`)

Für einen gezielten API-Check inkl. Request-ID-Korrelation:

```bash
DEV_BASE_URL="https://<endpoint>" \
SMOKE_REQUEST_ID="ops-smoke-001" \
./scripts/run_remote_api_smoketest.sh
```

Optionales Artefakt für Tickets/Reviews:

```bash
DEV_BASE_URL="https://<endpoint>" \
SMOKE_OUTPUT_JSON="artifacts/ops-smoke.json" \
./scripts/run_remote_api_smoketest.sh
```

Erwartung: Exit `0`, Status `pass`.

---

## 3) Kurzer Stabilitätslauf

Wenn ein einzelner Smoke-Test grün ist, aber Instabilität vermutet wird:

```bash
DEV_BASE_URL="https://<endpoint>" \
STABILITY_RUNS=3 \
STABILITY_INTERVAL_SECONDS=10 \
STABILITY_REPORT_PATH="artifacts/ops-stability.ndjson" \
./scripts/run_remote_api_stability_check.sh
```

Erwartung: Exit `0`, `pass`-Runs ohne unerwartete 5xx/Timeout-Spitzen.

---

## 4) Deploy-Runbook (User-/Support-Sicht)

### Vor Deploy

1. `./scripts/run_webservice_e2e.sh`
2. Optional: `./scripts/check_docs_quality_gate.sh` bei Doku-lastigen Änderungen
3. Prüfen, dass keine offenen kritischen Alerts aktiv sind

### Nach Deploy

1. Health prüfen (`/health`)
2. Smoke gegen `/analyze` ausführen
3. Bei Bedarf 3er-Stabilitätslauf starten
4. Request-ID + Artefakte im PR/Issue dokumentieren

---

## 5) Incident-Minirunbook

1. **Symptom bestätigen**
   - Health + Smoke ausführen
2. **Scope eingrenzen**
   - Nur lokal? Nur dev? Alle Requests?
3. **Diagnose-Artefakte sammeln**
   - HTTP-Status, Fehler-JSON, `request_id`, Smoke-/Stability-Report
4. **Kurzfristige Mitigation**
   - Siehe [`../DEPLOYMENT_AWS.md`](../DEPLOYMENT_AWS.md) (Redeploy/Rollback)
5. **Eskalation mit Evidenz**
   - reproduzierbarer Command + Output + `request_id` + Umgebung

---

## 6) Exit-Codes (relevant für Betrieb)

- `./scripts/run_webservice_e2e.sh`: `0` = grün, sonst fail
- `./scripts/run_remote_api_smoketest.sh`: `0` = pass, `2` = Eingabe-/Konfigfehler
- `./scripts/run_remote_api_stability_check.sh`: `0` = innerhalb Schwellwert, sonst fail
- `./scripts/check_docs_quality_gate.sh`: `0` = Doku-Gate grün

---

Weiterführend:
- [Getting Started](./getting-started.md)
- [Configuration / ENV](./configuration-env.md)
- [API Usage Guide](./api-usage.md)
- [Troubleshooting](./troubleshooting.md)
- [Operations (Infra/Team)](../OPERATIONS.md)
