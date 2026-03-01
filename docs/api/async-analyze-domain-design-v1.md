> **Diese Datei wurde konsolidiert.** Aktuelle kanonische Version: [async-v1.md](async-v1.md)

---

# Async-Analyze Domain-Design v1 (GTM Follow-up)

Stand: 2026-03-01  
Issue: #587 (Parent #577)

## Ziel des Work-Packages

Dieses Dokument präzisiert das asynchrone Domänenmodell für längere Analyze-Läufe,
sodass UX, API und Persistenz ohne Sync-Timeout-Abhängigkeit konsistent
weiterentwickelt werden können.

**Scope dieses Work-Packages (#587):**

- kanonische Job-States inkl. Fehler-/Cancel-Pfade
- Datenmodell für `jobs`, `job_events`, `job_results`, optionale `notifications`
- Progress-/Chunking-Strategie inkl. Partial Results
- UX-Flow mit Result-Page und permanentem `result_id`
- API-/Eventing-Schnittpunkte für spätere Implementierung

## 1) Job-State-Machine (verbindlich v1)

### 1.1 Kanonische States

| State | Bedeutung | Nutzerwirkung |
| --- | --- | --- |
| `queued` | Job akzeptiert, wartet auf Worker-Kapazität | Progress-UI zeigt Wartestatus |
| `running` | Verarbeitung aktiv | Progress steigt, Teilergebnisse möglich |
| `partial` | Teilresultat verfügbar, Endresultat noch offen | Nutzer kann Zwischenstand einsehen |
| `completed` | Finales Resultat persistiert | Result-Page final nutzbar |
| `failed` | Verarbeitung terminal fehlgeschlagen | Fehlergrund + Retry-Option |
| `canceled` | Job bewusst abgebrochen | UI zeigt Abbruchstatus, kein weiterer Compute |

### 1.2 Erlaubte Zustandstransitionen

| From | Trigger | To | Regel |
| --- | --- | --- | --- |
| `queued` | Worker startet Verarbeitung | `running` | `started_at` setzen |
| `queued` | Nutzer/System bricht vor Start ab | `canceled` | `canceled_by` + `cancel_reason` setzen |
| `running` | erstes validiertes Chunk-Resultat | `partial` | `partial_count >= 1` |
| `running` | Verarbeitung endet ohne Teilresultat | `completed` | `result_id` muss vorhanden sein |
| `running` | Fehler (terminal) | `failed` | `error_code` + `error_message` required |
| `running` | Nutzer/System bricht ab | `canceled` | Worker stoppt idempotent |
| `partial` | weitere Chunks / Fortschritt | `partial` | progress monotonic, Events append-only |
| `partial` | finale Aggregation erfolgreich | `completed` | finaler Snapshot in `job_results` |
| `partial` | terminaler Fehler | `failed` | vorhandene Partial Results bleiben lesbar |
| `partial` | Nutzer/System bricht ab | `canceled` | letzter Partial-Stand bleibt sichtbar |

**Nicht erlaubt (v1):** direkte Sprünge `queued -> completed` ohne
`running`, sowie `completed|failed|canceled -> running`.

### 1.3 Fehler- und Cancel-Pfade

- `failed` ist **terminal** und enthält mindestens:
  - `error_code`
  - `error_message`
  - `failed_at`
  - `retryable` (bool)
- `canceled` ist **terminal**, mit:
  - `canceled_by` (`user|system|worker`)
  - `cancel_reason`
  - `canceled_at`
- Bereits persistierte Partial Results bleiben bei `failed|canceled` erhalten
  (debug-/transparency-first).

## 2) Datenmodell v1 (`jobs`, `job_events`, `job_results`, `notifications`)

### 2.1 `jobs` (Steuer-/Lebenszyklusobjekt)

Mindestfelder:

- `job_id` (PK, UUID/ULID)
- `org_id`, `requested_by_user_id?`, `api_key_id?`
- `status` (`queued|running|partial|completed|failed|canceled`)
- `priority_class` (`default|expedite`)
- `request_payload_hash`, `request_payload_ref`
- `progress_percent` (0..100)
- `partial_count`, `error_count`
- `result_id?` (gesetzt ab `completed`, optional schon bei `partial`)
- `queued_at`, `started_at?`, `finished_at?`, `updated_at`
- `cancel_requested_at?`, `canceled_at?`, `canceled_by?`

Indizes (v1):

1. `idx_jobs_org_status_updated` auf (`org_id`, `status`, `updated_at desc`)
2. `idx_jobs_status_priority_queued` auf (`status`, `priority_class`, `queued_at`)
3. `idx_jobs_result_id` auf (`result_id`) (unique where not null)

### 2.2 `job_events` (append-only Event-Log)

Mindestfelder:

- `event_id` (PK)
- `job_id` (FK)
- `event_type` (z. B. `job.queued`, `job.started`, `job.partial`, `job.completed`, `job.failed`, `job.canceled`)
- `event_seq` (monoton pro Job)
- `occurred_at`
- `actor_type` (`system|worker|user`)
- `payload_json` (klein, redigiert)
- `trace_id`, `request_id`

Indizes (v1):

1. unique (`job_id`, `event_seq`)
2. `idx_job_events_job_occurred` auf (`job_id`, `occurred_at`)
3. `idx_job_events_type_occurred` auf (`event_type`, `occurred_at`)

### 2.3 `job_results` (Result-Snapshots)

Mindestfelder:

- `result_id` (PK/permalink key)
- `job_id` (FK, unique für finales Ergebnis)
- `result_kind` (`partial|final`)
- `result_seq` (monoton pro Job)
- `schema_version`
- `result_payload_ref` (Blob-/Object-Storage-Referenz)
- `summary_json` (UI-optimierter Kurzstand)
- `created_at`

Indizes (v1):

1. `idx_job_results_job_seq` auf (`job_id`, `result_seq`)
2. `idx_job_results_created` auf (`created_at desc`)
3. unique (`job_id`, `result_kind`) **nur** für `result_kind = final`

### 2.4 `notifications` (optional, out-of-band)

Mindestfelder:

- `notification_id` (PK)
- `job_id` (FK)
- `channel` (`in_app|email|webhook`)
- `template_key`
- `delivery_status` (`pending|sent|failed|suppressed`)
- `attempt_count`, `last_error?`
- `scheduled_at`, `sent_at?`

Indizes (v1):

1. `idx_notifications_job_channel` auf (`job_id`, `channel`)
2. `idx_notifications_delivery_status` auf (`delivery_status`, `scheduled_at`)

## 3) Progress-/Chunking-Strategie + Partial Results

### 3.1 Progress-Regeln

- `progress_percent` ist monoton steigend (`0 -> 100`).
- Fortschritts-Events werden über `job_events` persistiert.
- Progress-Sprünge ohne Event sind nicht zulässig (Auditierbarkeit).

### 3.2 Chunking-Modell

- Verarbeitung erfolgt in fachlichen Chunks (z. B. Datenquelle/Modul/Region).
- Jeder erfolgreiche Chunk darf ein `job.partial`-Event erzeugen.
- Partial-Output wird in `job_results` als `result_kind=partial` versioniert
  gespeichert (`result_seq` monotonic).

### 3.3 Partial-Result-Strategie

- UI darf bei State `partial` stets den letzten konsistenten Snapshot anzeigen.
- Bei `failed` bleibt letzter `partial`-Snapshot abrufbar.
- Bei `canceled` bleibt letzter konsistenter Snapshot mit Cancel-Hinweis abrufbar.
- Finalisierung (`completed`) erzeugt genau einen `result_kind=final` Snapshot.

## 4) UX-Flow (Progress, Completion, Result-Page)

1. Nutzer startet Analyse (bestehender Einstieg, additiv asynchron).
2. System liefert `job_id` + initialen Status `queued`.
3. Progress-UI pollt/streamt Job-Status (`queued|running|partial|...`).
4. Bei `partial`: UI zeigt Zwischenstand + Hinweis „läuft weiter“.
5. Bei `completed`: UI leitet auf permanente Result-Page mit `result_id` um.
6. Bei `failed`: UI zeigt Fehlerklasse + Retry-Empfehlung.
7. Bei `canceled`: UI zeigt Abbruch + optionalen Resume/Neu starten-Hinweis.

### Result-Page / Permalink-Regeln (v1)

- `result_id` ist stabiler, sharebarer Identifier.
- Zugriff bleibt tenant-gebunden (`org_id`-Scope, kein Cross-Tenant-Leak).
- Retention default:
  - Finale Results: 90 Tage
  - Partial Results: 14 Tage
  - Job-Events: 30 Tage (aggregierte Audit-Metadaten länger möglich)

## 5) API-/Eventing-Schnittpunkte (Vorbereitung für Implementierung)

### 5.1 API-Surface (additiv, v1-Zielbild)

- `POST /analyze` bleibt kompatibel und kann asynchronen Modus akzeptieren.
- `GET /analyze/jobs/{job_id}` liefert Job-Status + Progress + letzte Result-Referenz.
- `GET /analyze/results/{result_id}` liefert Snapshot (partial/final) tenant-sicher.
- `POST /analyze/jobs/{job_id}/cancel` stößt idempotenten Abbruch an.

### 5.2 Eventing-Mindestereignisse

- `api.analyze.job.queued`
- `api.analyze.job.started`
- `api.analyze.job.partial`
- `api.analyze.job.completed`
- `api.analyze.job.failed`
- `api.analyze.job.canceled`

Pflichtfelder je Event: `job_id`, `org_id`, `status`, `event_seq`, `occurred_at`,
`trace_id`, optional `result_id`.

### 5.3 Implementierungs-Guardrails

- Additiv/non-breaking gegenüber bestehendem Contract.
- Idempotente Status-/Cancel-Verarbeitung.
- Keine Persistenz- oder Event-Schreibpfade ohne `org_id`.
- Event-Emission erst nach erfolgreichem Persist-Schritt (no phantom events).

## 6) DoD-Abdeckung (#587)

- Zustandstransitionen inkl. Fehler-/Cancel-Pfade: Abschnitt 1
- Datenmodell inkl. Mindestfeldern + Indizes: Abschnitt 2
- UX-Flow für Progress/Completion/Result-Page: Abschnitt 4
- API-/Eventing-Schnittpunkte vorbereitet: Abschnitt 5

## Nächster Schritt

Oldest-first im Parent #577: #588 (MVP→Scale Rollout-Plan + atomisierbarer
Implementierungsfahrplan) umsetzen.
