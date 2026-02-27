# BL-20.y.wp2 — OpenClaw-Mapping für migrierbare GitHub-Workflows

Stand: 2026-02-27  
Parent: #220  
Work-Package: #222

## Ziel
Für alle in #221 als `migrate-to-openclaw` klassifizierten Workflows wird ein konkretes Ausführungsdesign festgelegt:

- Trigger (cron / event-surrogate / manuell)
- Session-Typ (isolated vs. main)
- Modell/Thinking
- Delivery-Verhalten (silent, announce-on-fail, summary)
- Retry-/Backoff-/Timeout-Policy
- Evidenzpfade (Logs/Reports)

## Standard-Policy (für alle OpenClaw-Jobs)

- **Isolation:** Automations laufen als isolierte Sessions/Sub-Agents, nicht im Main-Chat.
- **Modell:** `openai/gpt-5-mini` für Cron-Jobs (kostenkontrollierter Default).
- **Thinking:** `low`, nur bei klar begründetem Risiko auf `medium` erhöhen.
- **Retry:** max. 2 Wiederholungen (Backoff: 5 min, dann 15 min).
- **Timeout:** 20 min pro Run (hart), danach Fehlstatus + kurzer Blocker-Hinweis.
- **Delivery:** Standard `none`; bei Fehlern `announce-on-fail` (Issue-Kommentar oder definierter Kanal).
- **Evidenz:** Jeder Lauf schreibt unter `reports/automation/<job-id>/` mindestens `latest.md` und `history/<timestamp>.md`.

## Mapping-Tabelle (`migrate-to-openclaw`)

| Legacy Workflow | Quelle | OpenClaw Job-ID | Trigger | Session-Typ | Modell/Thinking | Delivery | Retry/Timeout | Evidenzpfad | Umsetzungsanker |
|---|---|---|---|---|---|---|---|---|---|
| contract-tests | `.github/workflows/contract-tests.yml` | `geo-ranking-contract-tests-surrogate` | `cron: */30 * * * *` + manueller Start | isolated/run | `openai/gpt-5-mini`, `low` | announce-on-fail | 2x (5m/15m), 20m | `reports/automation/contract-tests/` | `python3 scripts/validate_field_catalog.py` + `pytest -q tests/test_api_contract_v1.py tests/test_api_field_catalog.py` |
| crawler-regression | `.github/workflows/crawler-regression.yml` | `geo-ranking-crawler-regression-surrogate` | `cron: 15 * * * *` + manueller Start | isolated/run | `openai/gpt-5-mini`, `low` | announce-on-fail | 2x (5m/15m), 20m | `reports/automation/crawler-regression/` | `./scripts/check_crawler_regression.sh` |
| docs-quality | `.github/workflows/docs-quality.yml` | `geo-ranking-docs-quality-surrogate` | `cron: 45 */2 * * *` + manueller Start | isolated/run | `openai/gpt-5-mini`, `low` | announce-on-fail | 2x (5m/15m), 20m | `reports/automation/docs-quality/` | `./scripts/check_docs_quality_gate.sh` |
| worker-claim-priority | `.github/workflows/worker-claim-priority.yml` | `geo-ranking-worker-claim-reconciler` | event-surrogate via `cron: */10 * * * *` (Issue/Label-Reconcile) | isolated/run | `openai/gpt-5-mini`, `low` | summary (nur bei Mutationen) | 2x (5m/15m), 20m | `reports/automation/worker-claim-priority/` | Reconcile-Script für Label-/Claim-Order (Implementierung in #223) |

## Trigger-/Delivery-Entscheidungen (Kurzbegründung)

1. **contract-tests / crawler-regression / docs-quality**
   - laufen deterministisch und script-basiert → gute Cron-Kandidaten.
   - PR-Event-Parität wird MVP-seitig über häufige Surrogate-Läufe + Fehler-Delivery abgedeckt.

2. **worker-claim-priority**
   - benötigt Issue/Label-Event-Logik; OpenClaw übernimmt dies als periodischen Reconciler.
   - verhindert Billing-Abhängigkeit von GitHub Actions bei gleichzeitig reproduzierbarer Governance.

## Offene Risiken / Follow-up-Issues

- **R1: Event-Parität (Issue/PR-nahe Trigger) nur surrogate-basiert.**
  - Follow-up-Issue: **#227** (Webhook/Relay für schnellere Reaktionszeiten ohne Polling).
- **R2: Einheitliches Report-Schema für Automation-Artefakte fehlt noch.**
  - Umsetzung in #223, falls dort nicht vollständig: separates Follow-up anlegen.

## Nächste Schritte

1. #223 — Mindestens drei Jobs technisch migrieren und mit realer Evidenz laufen lassen.
2. #224 — Nicht mehr benötigte Actions + Required-Checks + Runbook final bereinigen.
