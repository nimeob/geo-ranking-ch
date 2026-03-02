# Testing Runbooks — Historische BL-31/BL-335/BL-337/BL-340 Evidence

Konsolidierung aus BL-31, BL-335, BL-337, BL-340 spezifischen Testing-Docs.  
Neue, nicht BL-spezifische Test-Runbooks gehören direkt in die Subdirectory-Dateien oder `docs/testing/`.

---

## BL-31.6.a — UI-Artefaktpfad + Task-Revision (dev)

*Quelle: `bl31-ui-artifact-path-taskdef-setup.md`*

**Scope:** Issue #345 — ECR `swisstopo-dev-ui`, UI Image Build/Push, ECS Task Definition.

```bash
IMAGE_TAG=$(git rev-parse --short HEAD) \
APP_VERSION=$(git rev-parse --short HEAD) \
UI_API_BASE_URL=https://api.geo.friedland.ai \
./scripts/setup_bl31_ui_artifact_path.sh
```

Evidence-Output: `artifacts/bl31/<stamp>-bl31-ui-artifact-path.json`

Ergebnis (2026-02-28):
- CodeBuild: `swisstopo-dev-api-openclaw-build:a9976f70-...` (SUCCEEDED)
- ECR Image: `523234426229.dkr.ecr.eu-central-1.amazonaws.com/swisstopo-dev-ui:561a5d1`
- Digest: `sha256:88a792bc54953016ffc299b4848f19b75f76ff502a4421f29c379c920decf2da`
- ECS Task Definition: `arn:aws:ecs:eu-central-1:523234426229:task-definition/swisstopo-dev-ui:3`

```bash
# Verifikation (read-only)
aws ecr describe-images --region eu-central-1 --repository-name swisstopo-dev-ui --image-ids imageTag=561a5d1
aws ecs describe-task-definition --region eu-central-1 --task-definition swisstopo-dev-ui:3
```

---

## BL-31.6.b — ECS UI-Service Rollout + Stabilisierung (dev)

*Quelle: `bl31-ui-ecs-rollout.md`*

**Scope:** Issue #346 — UI-Service `swisstopo-dev-ui` auf stabile Revision ausrollen.

```bash
# 1) Taskdef-Revision sicherstellen (BL-31.6.a Path)
IMAGE_TAG=$(git rev-parse --short HEAD) APP_VERSION=$(git rev-parse --short HEAD) \
  UI_API_BASE_URL=https://api.geo.friedland.ai ./scripts/setup_bl31_ui_artifact_path.sh

# 2) UI-Service ausrollen
TARGET_TASKDEF=swisstopo-dev-ui:5 ./scripts/setup_bl31_ui_service_rollout.sh
```

Evidence-Output: `artifacts/bl31/<stamp>-bl31-ui-ecs-rollout.json`

Ergebnis (2026-02-28):
- TaskDef Wechsel: `swisstopo-dev-ui:3` → `swisstopo-dev-ui:5`
- UI Service: `ACTIVE`, rollout `COMPLETED`, `desired=1`, `running=1`
- UI Health: `http://51.102.114.50:8080/healthz` → `{"ok": true, ...}`

**Rollback UI-only:**
```bash
aws ecs update-service --region eu-central-1 --cluster swisstopo-dev \
  --service swisstopo-dev-ui --task-definition arn:aws:ecs:eu-central-1:523234426229:task-definition/swisstopo-dev-ui:3
aws ecs wait services-stable --region eu-central-1 --cluster swisstopo-dev --services swisstopo-dev-ui
BL31_STRICT_CORS=1 ./scripts/run_bl31_routing_tls_smoke.sh
```

---

## BL-31.5 — UI Monitoring Baseline Check

*Quelle: `bl31-ui-monitoring-baseline-check.md`*

**Scope:** Issue #331 — Reproduzierbarer Read-only Check für getrennte API/UI Monitoring-Signale.

```bash
# Monitoring-Baseline bereitstellen (idempotent)
AWS_ACCOUNT_ID=523234426229 ./scripts/setup_bl31_ui_monitoring_baseline.sh

# API + UI prüfen
./scripts/check_monitoring_baseline_dev.sh
./scripts/check_bl31_ui_monitoring_baseline.sh
```

Exit-Codes: `0`=OK, `10`=Warn, `20`=kritisch

Alarms: `swisstopo-dev-ui-running-taskcount-low`, `swisstopo-dev-ui-health-probe-fail`

---

## BL-31.6.c — Kombinierter App/API/Monitoring-Lauf (dev)

*Quelle: `bl31-app-api-monitoring-evidence.md`*

**Scope:** Issue #347 — Kombinierter Smoke-/E2E-Lauf für App+API inkl. CORS-Baseline.

```bash
# 1) UI/API-Rollout-Evidenz
./scripts/setup_bl31_ui_service_rollout.sh

# 2) Monitoring-Baseline sichern
./scripts/openclaw_runtime_assumerole_exec.sh ./scripts/setup_bl31_ui_monitoring_baseline.sh

# 3) Kombinierter Lauf (CORS im Warn-Modus)
./scripts/openclaw_runtime_assumerole_exec.sh env \
  BL31_ROLLOUT_EVIDENCE=artifacts/bl31/<stamp>-bl31-ui-ecs-rollout.json \
  BL31_STRICT_CORS=0 \
  ./scripts/run_bl31_app_api_monitoring_evidence.sh
```

Output-Artefakte:
- `artifacts/bl31/*-bl31-routing-tls-smoke.json`
- `artifacts/bl31/*-bl31-ui-monitoring-baseline.log`
- `artifacts/bl31/*-bl31-app-api-monitoring-evidence.json`

Ergebnis (2026-02-28):
- API Health `/health`: pass
- UI Reachability `/healthz`: pass
- CORS-Baseline `OPTIONS /analyze`: warn (`missing_allow_origin` bei Task-IP-Origin)
- UI-Monitoring-Baseline: pass

---

## BL-31 Routing/TLS Smoke Catch-up

*Quelle: `bl31-routing-tls-smoke-catchup.md`*

**Scope:** Issue #336 — Reproduzierbarer Smoke für Routing/TLS-Änderungen.

### Baseline-Modus

```bash
# Terminal A (API)
HOST=127.0.0.1 PORT=18080 CORS_ALLOW_ORIGINS="http://127.0.0.1:18081" python3 -m src.api.web_service

# Terminal B (UI)
HOST=127.0.0.1 PORT=18081 UI_API_BASE_URL="http://127.0.0.1:18080" python3 -m src.ui.service

# Smoke
BL31_API_BASE_URL="http://127.0.0.1:18080" BL31_APP_BASE_URL="http://127.0.0.1:18081" \
BL31_CORS_ORIGIN="http://127.0.0.1:18081" BL31_STRICT_CORS="0" \
BL31_OUTPUT_JSON="artifacts/bl31-routing-tls-smoke-baseline.json" \
./scripts/run_bl31_routing_tls_smoke.sh
```

Erwartetes Ergebnis (nach #329): API-Health `pass`, APP-Reachability `pass`, CORS-Baseline `pass`.

### Strict-Modus (Abnahme)

```bash
BL31_API_BASE_URL="http://127.0.0.1:18080" BL31_APP_BASE_URL="http://127.0.0.1:18081" \
BL31_CORS_ORIGIN="http://127.0.0.1:18081" BL31_STRICT_CORS="1" \
./scripts/run_bl31_routing_tls_smoke.sh
```

Artefakt enthält: `overall.status/reason`, `checks.api_health.*`, `checks.app_reachability.*`, `checks.cors_baseline.*`

---

## BL-31 Smoke-/Evidence-Matrix (API-only, UI-only, Combined)

*Quelle: `bl31-smoke-evidence-matrix.md`*

```bash
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
export BL31_SMOKE_API_BASE_URL="https://api.<domain>"
export BL31_SMOKE_APP_BASE_URL="https://app.<domain>"
export BL31_SMOKE_CORS_ORIGIN="https://app.<domain>"

# Dry-Run
python3 scripts/run_bl31_split_deploy.py --mode api  --output-json "artifacts/bl31/${STAMP}-bl31-split-deploy-api.json"
python3 scripts/run_bl31_split_deploy.py --mode ui   --output-json "artifacts/bl31/${STAMP}-bl31-split-deploy-ui.json"
python3 scripts/run_bl31_split_deploy.py --mode both --output-json "artifacts/bl31/${STAMP}-bl31-split-deploy-both.json"

# Validieren
python3 scripts/check_bl31_smoke_evidence_matrix.py \
  "artifacts/bl31/${STAMP}-bl31-split-deploy-api.json" \
  "artifacts/bl31/${STAMP}-bl31-split-deploy-ui.json" \
  "artifacts/bl31/${STAMP}-bl31-split-deploy-both.json"
```

Pflicht-Felder: `mode`, `taskDefinitionBefore`, `taskDefinitionAfter`, `result`, `timestampUtc`

Status: `planned`=Dry-Run, `pass`=Erfolg, `fail`=nur mit Fehlerbeleg.

---

## BL-335 Frontdoor Runtime Guardrail

*Quelle: `bl335-frontdoor-runtime-guardrail.md`*

**Script:** `scripts/check_bl335_frontdoor_runtime.py`

Prüft: UI `/healthz` advertized `api_base_url` + CORS-Preflight `OPTIONS /analyze` für alle UI-Origins.

```bash
python3 scripts/check_bl335_frontdoor_runtime.py \
  --ui-health-url "https://www.dev.georanking.ch/healthz" \
  --api-analyze-url "https://api.dev.georanking.ch/analyze" \
  --expected-api-base-url "https://api.dev.georanking.ch" \
  --expected-ui-origin "https://www.dev.georanking.ch" \
  --expected-ui-origin "https://www.dev.geo-ranking.ch" \
  --output-json "artifacts/bl335/frontdoor-runtime-check.json"
```

Exit-Codes: `0`=pass, `1`=fachlicher Fail, `2`=Parameter-Fehler.  
Abgesichert durch: `tests/test_check_bl335_frontdoor_runtime.py`

---

## BL-335 Frontdoor Redeploy-Abnahme

*Quelle: `bl335-frontdoor-redeploy-acceptance-runbook.md`*

**Scope:** WP3 / Issue #379 — End-to-End-Abnahme nach Infra-Cutover.

```bash
export BL31_API_BASE_URL="https://api.dev.georanking.ch"
export BL31_APP_BASE_URL="https://www.dev.georanking.ch"
export BL31_CORS_ORIGIN="https://www.dev.georanking.ch"
export BL335_ALT_UI_ORIGIN="https://www.dev.geo-ranking.ch"
```

**1) HTTPS-Health:**
```bash
curl -fsS "${BL31_APP_BASE_URL}/healthz"
curl -fsS "${BL31_API_BASE_URL}/health"
```

**2) Runtime-Guardrail:**
```bash
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
python3 scripts/check_bl335_frontdoor_runtime.py \
  --ui-health-url "${BL31_APP_BASE_URL}/healthz" \
  --api-analyze-url "${BL31_API_BASE_URL}/analyze" \
  --expected-api-base-url "${BL31_API_BASE_URL}" \
  --expected-ui-origin "${BL31_CORS_ORIGIN}" --expected-ui-origin "${BL335_ALT_UI_ORIGIN}" \
  --output-json "artifacts/bl335/${STAMP}-frontdoor-runtime-check.json"
```

**3) API-only Redeploy:**
```bash
python3 scripts/run_bl31_split_deploy.py --mode api --execute \
  --smoke-api-base-url "${BL31_API_BASE_URL}" --smoke-app-base-url "${BL31_APP_BASE_URL}" \
  --smoke-cors-origin "${BL31_CORS_ORIGIN}" \
  --output-json "artifacts/bl31/${STAMP}-bl31-split-deploy-api-execute.json"
```

**4) UI-only Redeploy:** analog mit `--mode ui`.

**5) Post-Redeploy Guardrail:** erneut Schritt 2 ausführen.

**Parent-Abschluss-Checkliste (#376):**
- HTTPS Health app/api grün
- Runtime-Guardrail vor/nach Redeploy grün
- API-only + UI-only Redeploy grün
- Evidence-Artefakte verlinkt

---

## BL-337 Internet-E2E Matrix

*Quelle: `bl337-internet-e2e-matrix.md`*

**Scope:** WP1 / Issue #396 — Kanonisches Format für Internet-E2E-Tests gegen Dev-Frontdoors.

```bash
# Matrix erzeugen
python3 scripts/manage_bl337_internet_e2e_matrix.py \
  --output artifacts/bl337/latest-internet-e2e-matrix.json

# Validieren
python3 scripts/manage_bl337_internet_e2e_matrix.py \
  --validate artifacts/bl337/latest-internet-e2e-matrix.json

# Strict (Abschluss)
python3 scripts/manage_bl337_internet_e2e_matrix.py \
  --validate artifacts/bl337/latest-internet-e2e-matrix.json --require-actual
```

Pflicht-Felder: `testId`, `area`, `title`, `preconditions`, `steps`, `expectedResult`, `actualResult`, `status`, `evidenceLinks`, `notes`

Status-Werte: `planned`, `pass`, `fail`, `blocked`

**WP2 API-Frontdoor (Issue #397):**
```bash
python3 scripts/run_bl337_api_frontdoor_e2e.py \
  --matrix artifacts/bl337/latest-internet-e2e-matrix.json \
  --evidence-json artifacts/bl337/<timestamp>-wp2-api-frontdoor-e2e.json
```

**WP3 UI-Frontdoor (Issue #398):**
```bash
python3 scripts/run_bl337_ui_frontdoor_e2e.py \
  --matrix artifacts/bl337/latest-internet-e2e-matrix.json \
  --evidence-json artifacts/bl337/<timestamp>-wp3-ui-frontdoor-e2e.json
```

---

## Remote / Internet Smoke (staging/prod, sync + async)

*Quelle: `REMOTE_API_SMOKE_RUNBOOK.md`*

Reproduzierbare Entry-Points für Remote-Smokes (ohne BL-spezifischen Kontext), inkl. Evidence-Artefakte:
- Sync: `./scripts/run_staging_api_smoketest.sh`, `./scripts/run_prod_api_smoketest.sh`, `./scripts/run_remote_api_smoketest.sh`
- Async: `./scripts/run_staging_async_jobs_smoketest.sh`, `./scripts/run_prod_async_jobs_smoketest.sh`, `./scripts/run_remote_async_jobs_smoketest.sh`

---

## Dev: Self-Signed TLS + `/analyze` Smoke

*Quelle: `dev-self-signed-tls-smoke.md`*

```bash
# 1) Zertifikat erzeugen
./scripts/generate_dev_tls_cert.sh

# 2) API mit TLS starten
TLS_CERT_FILE=/tmp/geo-ranking-ch-dev-tls/dev-self-signed.crt \
TLS_KEY_FILE=/tmp/geo-ranking-ch-dev-tls/dev-self-signed.key \
API_AUTH_TOKEN=bl18-token PORT=8443 python -m src.api.web_service

# 3) HTTPS-Smoke
DEV_BASE_URL="https://localhost:8443" \
DEV_TLS_CA_CERT="/tmp/geo-ranking-ch-dev-tls/dev-self-signed.crt" \
DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" \
./scripts/run_remote_api_smoketest.sh
```

Erwartung: `PASS`, HTTP `200`, `ok=true`, `result` vorhanden.  
Automatisiert: `tests/test_remote_smoke_script.py::test_smoke_script_passes_against_self_signed_https_with_ca_cert`

---

## BL-340.4 — Upstream Trace Evidence

*Quelle: `BL-340_UPSTREAM_TRACE_EVIDENCE.md`*

Stand: 2026-03-01

### Artefakte
- Erfolgspfad: `artifacts/bl340/20260301T011200Z-upstream-trace-success.jsonl`
- Fehlerpfad: `artifacts/bl340/20260301T011215Z-upstream-trace-failure.jsonl`

### Erwartete Event-Kette

**Success:** `api.upstream.request.start` → `api.upstream.request.end` (status=ok) → `api.upstream.response.summary` (status=ok, records>0)

**Failure:** `api.upstream.request.start` → `api.upstream.request.end` (status=retrying, error_class=http_error) → `api.upstream.request.end` (status=error, finaler Fehlversuch)

### Reproduzierbare Checks
```bash
pytest -q tests/test_address_intel_upstream_logging.py tests/test_web_service_request_logging.py
```

Validiert: Presence der Events `api.upstream.request.start|end|response.summary`, Retry-/Error-Klassifikation, `request_id`/`session_id` Durchreichung.
