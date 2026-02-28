# BL-31.6.b Nachweis: ECS UI-Service Rollout + Stabilisierung (dev)

## Scope
Issue #346 (`BL-31.6.b`):
- UI-Service `swisstopo-dev-ui` in ECS `dev` auf stabile Revision ausrollen
- Healthcheck `/healthz` grün verifizieren
- API-Service-Parität (`swisstopo-dev-api`) unverändert erreichbar nachweisen
- Rollback-Hinweis dokumentieren

## Reproduzierbarer Lauf

```bash
# 1) Taskdef-Revision sicherstellen (BL-31.6.a Path)
IMAGE_TAG=$(git rev-parse --short HEAD) \
APP_VERSION=$(git rev-parse --short HEAD) \
UI_API_BASE_URL=https://api.geo.friedland.ai \
./scripts/setup_bl31_ui_artifact_path.sh

# 2) UI-Service auf Ziel-Revision ausrollen + Stabilitätschecks
TARGET_TASKDEF=swisstopo-dev-ui:5 \
./scripts/setup_bl31_ui_service_rollout.sh
```

Der Rollout-Check schreibt eine maschinenlesbare Evidenz nach `artifacts/bl31/*-bl31-ui-ecs-rollout.json`.

## Ergebnis (2026-02-28)

Evidence-Dateien:
- `artifacts/bl31/20260228T080633Z-bl31-ui-artifact-path.json`
- `artifacts/bl31/20260228T080756Z-bl31-ui-ecs-rollout.json`

Verifiziert:
- UI TaskDef Wechsel: `swisstopo-dev-ui:3` → `swisstopo-dev-ui:5`
- UI Service Status: `ACTIVE`, rollout `COMPLETED`, `desired=1`, `running=1`
- UI Health: `http://51.102.114.50:8080/healthz` → `{"ok": true, ...}`
- API unverändert: `swisstopo-dev-api:96` vor/nach Rollout identisch, `/health` erfolgreich

## Rollback-Pfad (UI-only)

Rollback auf die vorherige stabile UI-Revision (hier `:3`):

```bash
aws ecs update-service \
  --region eu-central-1 \
  --cluster swisstopo-dev \
  --service swisstopo-dev-ui \
  --task-definition arn:aws:ecs:eu-central-1:523234426229:task-definition/swisstopo-dev-ui:3

aws ecs wait services-stable \
  --region eu-central-1 \
  --cluster swisstopo-dev \
  --services swisstopo-dev-ui
```

Danach Pflicht-Smoke:

```bash
BL31_STRICT_CORS=1 ./scripts/run_bl31_routing_tls_smoke.sh
```
