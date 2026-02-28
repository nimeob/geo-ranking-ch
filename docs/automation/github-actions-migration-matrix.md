# GitHub Actions → OpenClaw Migrationsmatrix

Stand: 2026-02-28  
Parent: #220  
Work-Package: #221

## Ziel
Reproduzierbare Ist-Aufnahme aller aktuellen Workflows unter `.github/workflows/` mit klarer Zielklassifikation:

- `keep-on-github` (zwingend auf GitHub belassen)
- `migrate-to-openclaw` (nach OpenClaw überführen)
- `retire` (ersetzen/entfernen)

## Inventar + Klassifikation

| Workflow | Datei | Trigger heute | Zweck | Kritikalität | Zielentscheidung | Begründung |
|---|---|---|---|---|---|---|
| Deploy to AWS (ECS dev) | `.github/workflows/deploy.yml` | `push(main)` bei app/infra-Änderungen, `workflow_dispatch` | Build/Test + ECS Deploy inkl. Smoke-Checks | hoch | `keep-on-github` (MVP) | OIDC-Deploypfad über GitHub ist bereits etabliert und auditierbar; bis OpenClaw-Äquivalent inkl. Branch-Gates verifiziert ist, bleibt dieser Pfad minimal bestehen. |
| contract-tests | `.github/workflows/contract-tests.yml` | `push`/`pull_request` auf API-Contract-Pfade, `workflow_dispatch` | Contract-/Schema-Regressionen + Feldkatalog-Validierung | mittel | `migrate-to-openclaw` | Deterministische Testläufe können als OpenClaw Job (event-surrogate/cron + PR-Kommentar) kosteneffizient übernommen werden. |
| crawler-regression | `.github/workflows/crawler-regression.yml` | `push(main)`/`pull_request` auf Crawler-Pfade, `workflow_dispatch` | Regressionstest für Consistency-Crawler | mittel | `migrate-to-openclaw` | Read-only Crawler-Regression passt gut zu OpenClaw-Scheduler + Artefaktablage in Repo/Reports. |
| docs-quality | `.github/workflows/docs-quality.yml` | `push(main)`/`pull_request` auf Doku-Pfade | Doku-Link-/Struktur-Qualitätsgate | mittel | `migrate-to-openclaw` | Doku-Gates sind script-basiert (`scripts/check_docs_quality_gate.sh`) und direkt als OpenClaw Job reproduzierbar. |
| worker-claim-priority | `.github/workflows/worker-claim-priority.yml` | Issue-Events (`opened/reopened/closed/labeled/...`) + `workflow_dispatch` | Erzwingt Priority-Claim-Order per Label-Mutationen | hoch | `migrate-to-openclaw` | Eventlogik ist rein GitHub-API-basiert und kann als OpenClaw Event-Surrogate (periodischer Reconciler) stabiler/kostengünstiger laufen. |
| bl20-sequencer | ~~`.github/workflows/bl20-sequencer.yml`~~ (entfernt in #384) | `issues.closed`, `workflow_dispatch` (historisch) | Öffnet statische nächste BL-20-Issues in Reihenfolge | niedrig | `retire` | Sequenzliste ist statisch (Issue-ID-Reihe 22–38) und deckt die aktuelle Work-Package-Struktur nicht mehr sinnvoll ab; durch Worker-Claim-Flow ersetzbar. Workflow-Datei wurde final aus dem Repo entfernt. |

## Ergebniszusammenfassung

- Gesamt-Workflows erfasst: **6/6**
- `keep-on-github` (MVP): **1**
- `migrate-to-openclaw`: **4**
- `retire`: **1**

## Folgepfad

1. ✅ #222: OpenClaw-Mapping v1 spezifiziert in [`docs/automation/openclaw-job-mapping.md`](openclaw-job-mapping.md) (Trigger, Session-Typ, Modell/Thinking, Delivery, Retry/Timeout).
2. ✅ #223: Mindestens drei Workflows technisch migriert und Evidenzpfade standardisiert.
3. ✅ #224: Bereinigung verbliebener Actions + Required-Checks/Runbook-Sync.
4. ✅ #227: Event-Relay-Zielbild (Events, Security, Migration/Fallback) dokumentiert in [`docs/automation/openclaw-event-relay-design.md`](openclaw-event-relay-design.md).
5. ✅ #233: Event-Relay-Pfad inkl. Receiver/Queue/Consumer umgesetzt (`scripts/run_event_relay_receiver.py`, `scripts/run_event_relay_consumer.py`) mit dokumentiertem Security-/Hybrid-Betriebspfad.

## WP4/BL-336-Resultat (2026-02-28)

- `deploy.yml`: bleibt automatischer GitHub-Pfad (`push main` + `workflow_dispatch`).
- `contract-tests.yml`, `crawler-regression.yml`, `docs-quality.yml`: bleiben auf `workflow_dispatch` als manueller Fallback (Primärpfad OpenClaw).
- `bl20-sequencer.yml`: retired und in #384 final aus dem Repo entfernt.
- `worker-claim-priority.yml`: Deaktivierungsmarker ist noch **nicht** erfüllt; Workflow wurde in #384 wieder aktiviert (Hybrid-Betrieb bis Marker-Freigabe, siehe `docs/OPERATIONS.md`).
