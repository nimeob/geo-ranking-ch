# MVP→Scale Rollout-Plan v1 (GTM Follow-up)

Stand: 2026-03-01  
Issue: #588 (Parent #577)

## Ziel des Work-Packages

Dieses Dokument liefert einen risikoarmen, **additiven** Stufenplan von der
bestehenden Sync-Analyze-Basis zum skalierbaren Async-Betrieb inklusive
klarer Implementierungszerlegung in kleine Work-Issues.

## 1) Leitplanken (verbindlich)

1. **Keine Breaking Contracts:** bestehender `POST /analyze`-Pfad bleibt kompatibel.
2. **Additive Persistenz:** neue Async-Tabellen/Stores ergänzen bestehende Datenflüsse.
3. **Tenant-Sicherheit zuerst:** jeder Job-/Result-Zugriff bleibt strikt `org_id`-gebunden.
4. **Observability by default:** State-Übergänge, Fehler und Cancels sind nachvollziehbar.
5. **Rollback-fähige Stufen:** jede Phase ist separat deploybar und bei Bedarf reversibel.

## 2) Stufenplan MVP→Scale

### Phase A — Runtime-Skeleton (MVP-Start)

**Ziel:** persistenter Job-Grundpfad + Status-Read-API verfügbar.

- `jobs` + `job_events` Basisschema
- asynchroner Einstieg ohne UI-Bruch
- `GET /analyze/jobs/{job_id}` und `GET /analyze/results/{result_id}` Grundvertrag

**Exit-Kriterien:**

- Jobs sind dauerhaft nachvollziehbar (`queued|running|completed|failed|canceled`)
- State-Transitions sind deterministisch und testbar
- Backward-Compatibility für Sync-Clients bleibt intakt

### Phase B — Worker + Partial Results (MVP+)

**Ziel:** echte Langläuferausführung mit Progress- und Partial-Snapshots.

- Worker-/Dispatcher-Pfad für Queue-Verarbeitung
- `job.partial`-Events + `job_results` (`partial`)
- idempotenter Cancel-/Fehlerpfad

**Exit-Kriterien:**

- reproduzierbare Läufe `queued -> partial -> completed`
- Cancel-/Failure-Pfade stabil und regressionsgesichert
- Partial Results UI-/API-seitig abrufbar

### Phase C — Result Delivery + Operations (Scale-ready)

**Ziel:** produktreife Auslieferung mit Retention, Notifications und Betriebsfähigkeit.

- tenant-sichere Result-Permalinks (`result_id`)
- Retention-Cleanup für Results/Events gemäß TTL
- Notifications (mindestens `in_app`) für Completion/Failure
- Monitoring-/Runbook-Standard für Async-Betrieb

**Exit-Kriterien:**

- Result-Page und Retention laufen stabil in Prod-Bedingungen
- Completion/Failure-Benachrichtigungen sind nachweisbar
- Ops kann Fehlerpfade/Backlog/Queue-Lag aktiv überwachen

## 3) Risiken + Mitigations pro Stufe

| Phase | Risiko | Auswirkung | Mitigation |
| --- | --- | --- | --- |
| A | State-Drift durch inkonsistente Übergänge | falsche Job-Statusanzeige | zentrale Transition-Policy + Guard-Tests |
| A | versteckte Contract-Breaks für Legacy-Clients | Client-Fehler bei Rollout | additive Felder, bestehende Response-Semantik unverändert |
| B | Worker-Replays erzeugen doppelte Side-Effects | inkonsistente Partial-/Final-States | idempotente Event-/Result-Keys und dedup guards |
| B | Cancel race (`running` vs. `completed`) | falscher terminaler Zustand | atomare Finalisierung + last-write-guard auf terminal states |
| C | Retention löscht zu aggressiv | Datenverlust/Support-Aufwand | staged TTL rollout + dry-run reports + restore window |
| C | Notification-Spam oder Zustellfehler | schlechte UX/unnötige Last | channel-spezifische rate limits + delivery status tracking |

## 4) No-regrets Defaults + Trade-offs

### No-regrets Defaults

- monotone `event_seq` pro Job (`job_events` append-only)
- eindeutiger `result_id` als stabiler Permalink-Key
- terminale States sind unveränderlich (`completed|failed|canceled`)
- Cleanup-Jobs mit Dry-run-Modus vor Hard-Delete
- Mindesttelemetrie je Statuswechsel (`job_id`, `org_id`, `status`, `occurred_at`)

### Transparente Trade-offs

1. **Schneller MVP-Start vs. volle Queue-Infrastruktur**
   - Entscheidung: zuerst Dispatcher-light, später skalierbare Queue-Härtung.
2. **Partial-Granularität vs. Persistenzkosten**
   - Entscheidung: fachliche Chunk-Snapshots statt Event-pro-Mikroschritt.
3. **Retention-Kürze vs. Debug-Tiefe**
   - Entscheidung: kurze TTL für große Payloads, längere aggregierte Audit-Metadaten.

## 5) Atomisierte Folge-Issues (0.5–2 Tage)

- **#592** — BL-30.wp4.r1: Async Analyze Runtime Skeleton (Jobs API + Persistence)
- **#593** — BL-30.wp4.r2: Worker Execution + Partial Results/Eventing Pipeline
- **#594** — BL-30.wp4.r3: Result-Page Delivery + Retention/Notification Jobs

Abhängigkeitskette (oldest-first): **#592 -> #593 -> #594**.

## 6) Abnahmekriterien für Abschluss von #577

Parent #577 gilt als abschließbar, wenn alle folgenden Punkte erfüllt sind:

1. Work-Package-Checklist vollständig (`#585/#586/#587/#588` auf `[x]`).
2. GTM→DB-Architektur, Billing-/Entitlement-Lifecycle, Async-Domain-Design und Rollout-Plan sind dokumentiert und verlinkt.
3. Folge-Issues für Implementierung sind atomisiert (mindestens #592/#593/#594) und korrekt gelabelt (`backlog`, Priorität, Status).
4. BACKLOG-Sync enthält den aktuellen Status inkl. Next Steps.
5. Parent-DoD ist inhaltlich durch die vier Work-Packages nachweisbar abgedeckt.

## DoD-Abdeckung (#588)

- Stufenplan MVP→Scale mit Guardrails: Abschnitt 2
- Risiken + Mitigations pro Stufe: Abschnitt 3
- Mindestens 3 konkrete Folge-Issues mit DoD: Abschnitt 5 + Issues #592/#593/#594
- Abnahmekriterien für #577: Abschnitt 6

## Nächster Schritt

Oldest-first Umsetzung starten mit **#592**, danach #593 und #594; anschließend
Parent #577 finalisieren/schließen.
