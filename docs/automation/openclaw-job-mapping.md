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
| worker-claim-priority | `.github/workflows/worker-claim-priority.yml` | `geo-ranking-worker-claim-reconciler` | event-surrogate via `cron: */10 * * * *` (Ist) + Relay-Hybrid-Zielpfad gemäß #227/#233 | isolated/run | `openai/gpt-5-mini`, `low` | summary (nur bei Mutationen) | 2x (5m/15m), 20m | `reports/automation/worker-claim-priority/` | Reconcile-Script für Label-/Claim-Order (WP4) + Event-Relay-Design (`docs/automation/openclaw-event-relay-design.md`) + Consumer-Prototyp (`scripts/run_event_relay_consumer.py`) |

## Umsetzung in #223 (technischer Migrationsanker)

Für die drei MVP-Jobs aus #223 wurde ein gemeinsamer Runner eingeführt:

- Script: `scripts/run_openclaw_migrated_job.py`
- Unterstützte Job-IDs: `contract-tests`, `crawler-regression`, `docs-quality`
- Report-Schema pro Lauf:
  - `reports/automation/<job-id>/latest.json`
  - `reports/automation/<job-id>/latest.md`
  - `reports/automation/<job-id>/history/<timestamp>.json`
  - `reports/automation/<job-id>/history/<timestamp>.md`

Der Runner beendet sich mit dem Exit-Code des fehlgeschlagenen Schritts und kann damit direkt als OpenClaw-Cron-/Subagent-Entry genutzt werden.

## Trigger-/Delivery-Entscheidungen (Kurzbegründung)

1. **contract-tests / crawler-regression / docs-quality**
   - laufen deterministisch und script-basiert → gute Cron-Kandidaten.
   - PR-Event-Parität wird MVP-seitig über häufige Surrogate-Läufe + Fehler-Delivery abgedeckt.

2. **worker-claim-priority**
   - benötigt Issue/Label-Event-Logik; OpenClaw übernimmt dies als periodischen Reconciler.
   - verhindert Billing-Abhängigkeit von GitHub Actions bei gleichzeitig reproduzierbarer Governance.

## Offene Risiken / Follow-up-Issues

- **R1: Event-Parität (Issue/PR-nahe Trigger) ist dokumentiert, aber technisch noch nicht produktiv umgesetzt.**
  - ✅ Design/Target-State in **#227** und `docs/automation/openclaw-event-relay-design.md` festgelegt.
  - ⏳ Implementierungsfolge: **#233** (Relay-Receiver, Queue, OpenClaw-Consumer, Runbook-Sync), inkl. ✅ WP1 #236 (Consumer-Fundament).
- **R2: Worker-Claim-Reconciliation ist operativ noch cron-dominiert.**
  - Bis Abschluss von #233 bleibt der periodische Reconciler der maßgebliche Fallback-/Safety-Pfad.

## Nächste Schritte

1. ✅ #223 — Mindestens drei Jobs technisch migriert und mit realer Evidenz unter `reports/automation/*` nachgewiesen.
2. ✅ #224 — Nicht mehr benötigte Actions bereinigt/deaktiviert, Required-Checks-/Recovery-Runbook in `docs/OPERATIONS.md` ergänzt.
3. ✅ #227 — Event-Relay-Zielpfad (Events, Sicherheitsanforderungen, Migrations-/Fallback-Plan) dokumentiert.
4. ⏳ #233 — Event-Relay-Zielpfad produktionsnah implementieren und mit Evidenzpfaden absichern.
