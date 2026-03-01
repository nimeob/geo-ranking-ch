# BL-31.6.c Nachweis: Kombinierter App/API/Monitoring-Lauf + Parent-Sync (dev)

## Scope
Issue #347 (`BL-31.6.c`):
- kombinierten Smoke-/E2E-Lauf für App+API inkl. CORS-Baseline reproduzierbar ausführen
- UI-Monitoring-Baseline (`check_bl31_ui_monitoring_baseline.sh`) aktiv prüfen und dokumentieren
- Parent-Sync für #344/#327/#326 mit belastbarer Evidence fortschreiben

## Reproduzierbarer Lauf

```bash
# 1) Frische UI/API-Rollout-Evidenz erzeugen
./scripts/setup_bl31_ui_service_rollout.sh

# 2) Monitoring-Baseline einmalig provisionieren/absichern (idempotent)
./scripts/openclaw_runtime_assumerole_exec.sh ./scripts/setup_bl31_ui_monitoring_baseline.sh

# 3) Kombinierter Nachweislauf (CORS-Baseline im Warnmodus)
./scripts/openclaw_runtime_assumerole_exec.sh env \
  BL31_ROLLOUT_EVIDENCE=artifacts/bl31/<stamp>-bl31-ui-ecs-rollout.json \
  BL31_STRICT_CORS=0 \
  ./scripts/run_bl31_app_api_monitoring_evidence.sh
```

Output-Artefakte:
- `artifacts/bl31/*-bl31-routing-tls-smoke.json`
- `artifacts/bl31/*-bl31-routing-tls-smoke.log`
- `artifacts/bl31/*-bl31-ui-monitoring-baseline.log`
- `artifacts/bl31/*-bl31-app-api-monitoring-evidence.json`

## Ergebnis (2026-02-28)

Evidence-Dateien:
- `artifacts/bl31/20260228T082637Z-bl31-ui-ecs-rollout.json`
- `artifacts/bl31/20260228T083257Z-bl31-routing-tls-smoke.json`
- `artifacts/bl31/20260228T083257Z-bl31-ui-monitoring-baseline.log`
- `artifacts/bl31/20260228T083257Z-bl31-app-api-monitoring-evidence.json`

Verifiziert:
- API-Health (`/health`) pass
- UI-Reachability (`/healthz`) pass
- CORS-Baseline (`OPTIONS /analyze`) als Warnsignal dokumentiert (`missing_allow_origin` bei Task-IP-Origin)
- UI-Monitoring-Baseline-Check pass (`Ergebnis: OK`, Alarm/Probe operativ)
- Kombinierter Nachweis inkl. Input-/Output-Referenzen maschinenlesbar gespeichert
