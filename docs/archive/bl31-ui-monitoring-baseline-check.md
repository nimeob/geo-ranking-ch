# BL-31.5 UI Monitoring Baseline Check (Issue #331)

Ziel: reproduzierbarer Read-only Check für getrennte Monitoring-Signale von API und UI.

## Voraussetzungen

- AWS CLI konfiguriert (read-only genügt für Check)
- Zugriff auf `swisstopo-dev` Ressourcen

## 1) UI-Monitoring-Baseline bereitstellen (idempotent)

```bash
AWS_ACCOUNT_ID=523234426229 ./scripts/setup_bl31_ui_monitoring_baseline.sh
```

Legt an/aktualisiert:
- Alarm `swisstopo-dev-ui-running-taskcount-low`
- Reachability-Probe (Lambda/Rule/Alarm):
  - `swisstopo-dev-ui-health-probe`
  - `swisstopo-dev-ui-health-probe-schedule`
  - `swisstopo-dev-ui-health-probe-fail`

## 2) API + UI Read-only prüfen

```bash
# bestehende API-Baseline
./scripts/check_monitoring_baseline_dev.sh

# neue UI-Baseline
./scripts/check_bl31_ui_monitoring_baseline.sh
```

Erwartete Exit-Codes (beide Scripts):
- `0` = OK
- `10` = Warn
- `20` = kritisch

## 3) Nachweisformat für Issue-/PR-Kommentar

```text
Monitoring check:
- API baseline: <exit + Kernaussage>
- UI baseline:  <exit + Kernaussage>
- SNS routing:  <ok/warn>
```

Beispiel:

```text
Monitoring check:
- API baseline: exit 0 (alle Kernchecks grün)
- UI baseline: exit 0 (RunningTaskCount + Reachability-Probe grün)
- SNS routing: ok (Alarm-Actions enthalten swisstopo-dev-alerts)
```
