# BL-20.y.wp2.r1 — Event-Relay-Design für Issue/PR-nahe OpenClaw-Automation

Stand: 2026-02-27  
Parent: #220  
Work-Package: #227

## Kontext
Die OpenClaw-Migration aus #220 nutzt für Issue-/PR-nahe Governance aktuell Cron-Surrogates. Das funktioniert robust, erzeugt aber unnötige Polling-Läufe und reagiert träge.

Wichtige Randbedingung: Der OpenClaw-Container ist nicht direkt aus dem Internet erreichbar (kein inbound Webhook-Target). Deshalb ist **kein Direkt-Webhook auf den Container** möglich.

## Ziel
Ein webhook-/relay-gestützter Triggerpfad soll die Reaktionszeit für ausgewählte Automationsfälle senken und Polling reduzieren, ohne die Inbound-Restriktion des Containers zu verletzen.

## Ziel-Events und Reaktionszeit

| Event-Familie | Konkrete GitHub-Events | Primärer Consumer | Ziel-Reaktionszeit |
|---|---|---|---|
| Issue-Claim-Governance | `issues.opened`, `issues.reopened`, `issues.labeled`, `issues.unlabeled`, `issues.edited`, `issues.closed` | Worker-Claim-Reconciler | p95 ≤ 90s, max 3 min |
| PR-nahe Qualitätsjobs (MVP light) | `pull_request.opened`, `pull_request.synchronize`, `pull_request.reopened`, `pull_request.labeled` | Contract-/Docs-/Crawler-Surrogates (event-angestoßen) | p95 ≤ 3 min, max 10 min |
| Recovery/Backlog-Drift | `workflow_dispatch` + geplanter Fallback-Cron | Reconcile-/Audit-Jobs | ≤ 15 min (Fallback) |

## Technischer Zielpfad (ohne Container-Ingress)

1. **GitHub → Public Relay Endpoint**
   - GitHub Webhook sendet Events an einen extern erreichbaren Relay-Endpunkt (z. B. Cloud-Function/Worker).
   - Endpoint nimmt nur erlaubte Event-Typen entgegen (Allowlist).

2. **Relay Validation + Reduction**
   - Signaturprüfung (`X-Hub-Signature-256`) gegen hinterlegtes Secret.
   - Delivery-ID-Dedup (`X-GitHub-Delivery`) mit TTL.
   - Payload-Reduktion auf minimale Felder (`repo`, `event`, `action`, `issue/pr number`, `labels`, `delivery_id`, `timestamp`).

3. **Relay Queue/Store (durable)**
   - Validierte Events werden in eine durable Queue/Inbox geschrieben.
   - Event-Envelope folgt einem minimalen, maschinenlesbaren Schema: `docs/automation/event-relay-envelope.schema.json`.
   - Consumer-seitige Ack- oder Lease-Semantik, damit keine Event-Verluste bei Retry/Crash entstehen.

4. **OpenClaw Consumer (outbound pull)**
   - OpenClaw pollt die Queue aktiv outbound (z. B. jede Minute) und verarbeitet neue Events.
   - Repo-seitiger Consumer-Entrypoint: `scripts/run_event_relay_consumer.py`.
   - Kein externer Inbound-Zugriff auf den Container nötig.

5. **Dispatch in bestehende Jobs**
   - Routing zu bestehenden Automationspfaden (Worker-Claim-Reconciler, Contract-/Docs-/Crawler-Jobs).
   - Bei fehlgeschlagenem Event-Run greift der periodische Fallback-Cron.

## Sicherheitsanforderungen (verbindlich)

- **Authentizität:** Webhook-Signaturprüfung ist Pflicht; ungültige Signaturen werden verworfen.
- **Replay-Schutz:** Delivery-ID-Dedup + Zeitfensterprüfung.
- **Least Privilege:** Separate Tokens/Rollen für Relay-Write und Consumer-Read; keine überbreiten Repo-Rechte.
- **Secret-Hygiene:** Secrets nur im Secret-Store, nie im Repo/Logs.
- **Datenminimierung:** Keine vollständigen GitHub-Payloads dauerhaft speichern; nur technische Minimalfelder.
- **Auditierbarkeit:** Jede Event-Verarbeitung erhält Run-ID, Delivery-ID und Outcome (`processed|ignored|failed`).
- **Rate-Limits/Backpressure:** Queue-Limits, Retry mit Backoff, Dead-Letter-Mechanismus für toxische Events.

## Migrations- und Fallback-Plan

### Phase 0 — Bestand (aktiv)
- Cron-Surrogates bleiben der Produktionspfad.
- `worker-claim-priority.yml` bleibt als bestehende Event-Automation auf GitHub aktiv.

### Phase 1 — Shadow-Mode
- Relay empfängt/validiert Events, aber triggert nur read-only Vergleichs-Reports.
- Vergleich zwischen Event-Pfad und Cron-Ergebnis (Drift/Fehltrigger) wird dokumentiert.

### Phase 2 — Hybrid-Mode
- Event-Pfad wird primär für Issue-Claim-Governance genutzt.
- Fallback-Cron bleibt aktiv (z. B. alle 15 min) und korrigiert Ausfälle/Drift.

### Phase 3 — Event-first (stabilisiert)
- Event-Pfad ist Standard, Cron dient nur noch als degradierbarer Safety-Net.
- GitHub-Workflow `worker-claim-priority.yml` darf erst nach erfülltem Deaktivierungsmarker stillgelegt werden (mind. 2 saubere Live-Hybrid-Runs ohne Dispatch-Fehler + dokumentierter Drift-Abgleich + benannter Rollback-Owner).

## Betriebs-/Evidenzanforderungen

Für Relay-/Consumer-Läufe sollen konsistente Artefakte unter `reports/automation/event-relay/` entstehen (mindestens `latest.md` plus History-Dateien mit Zeitstempel).

## Follow-up

- **Implementierungsfolge (Parent):** #233 ✅ abgeschlossen
  - ✅ #236: Event-Envelope + Queue-Consumer-Fundament
  - ✅ #237: Issue-/Label-Dispatch in Worker-Claim-Reconcile (inkl. Sequenztests `labeled`/`unlabeled`/`reopened`)
  - ✅ #238: Shadow-/Hybrid-Rollout + Security-Runbook + Evidenzläufe (`20260227T090700Z`, `20260227T090900Z`)
  - ✅ #233 Abschlussdelta: Relay-Receiver für Ingress-Härtung (`scripts/run_event_relay_receiver.py`, Signaturprüfung + Repository-Allowlist + Delivery-Dedup)
- Bis der Deaktivierungsmarker erfüllt ist, bleibt der Cron-basierte Surrogate-Pfad produktiv maßgeblich.
