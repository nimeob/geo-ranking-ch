# GitHub Actions → OpenClaw Migrationsmatrix

Stand: 2026-02-27  
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
| bl20-sequencer | `.github/workflows/bl20-sequencer.yml` | `issues.closed`, `workflow_dispatch` | Öffnet statische nächste BL-20-Issues in Reihenfolge | niedrig | `retire` | Sequenzliste ist statisch (Issue-ID-Reihe 22–38) und deckt die aktuelle Work-Package-Struktur nicht mehr sinnvoll ab; durch Worker-Claim-Flow ersetzbar. |

## Ergebniszusammenfassung

- Gesamt-Workflows erfasst: **6/6**
- `keep-on-github` (MVP): **1**
- `migrate-to-openclaw`: **4**
- `retire`: **1**

## Folgepfad

1. #222: Für alle `migrate-to-openclaw` Workflows das konkrete OpenClaw-Mapping (Trigger, Session-Typ, Modell/Thinking, Delivery, Retry/Timeout) spezifizieren.
2. #223: Mindestens drei Workflows technisch migrieren und Evidenzpfade standardisieren.
3. #224: Bereinigung verbliebener Actions + Required-Checks/Runbook-Sync.
