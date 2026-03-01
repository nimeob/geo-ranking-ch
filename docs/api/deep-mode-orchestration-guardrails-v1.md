# BL-30.3.wp2 — Deep-Mode-Orchestrierung + Runtime-Guardrails (Design v1)

Stand: 2026-03-01  
Issue: #469 (Parent #107)

## Ziel

Ein umsetzbares Design für die **optionale Deep-Mode-Ausführung pro `/analyze`-Request** bereitstellen,
inklusive deterministischer Guardrails für Laufzeit/Kosten, klarer Trennung zur Basis-Analyse und
messbarer Telemetrie.

## Scope (dieses Work-Package)

- Ausführungssequenz Deep-Mode (Trigger, Budgetierung, Retry-/Abort-Regeln)
- Trennung Basis-Analyse (`baseline`) vs. Deep-Enrichment (`deep`)
- Schnittstellen zum bestehenden Analyze-Flow benennen
- Logging-/Tracing-Mindestanforderungen für reproduzierbare Debugbarkeit definieren

## Nicht-Ziele (in #469 bewusst nicht umgesetzt)

- Keine Runtime-Implementierung des Orchestrators in `src/api/web_service.py`
- Keine finalen Produkt-/Quota-Policies (siehe BL-30.3.wp3, #470)
- Kein Hard-Gate über Pricing/Checkout (abhängig von BL-30.2)

## Schnittstellen zum bestehenden Analyze-Flow

### Request-Eingang (`src/api/web_service.py`)

1. Request-Parsing und Basis-Validierung laufen unverändert.
2. Deep-Mode wird nur aus dem bereits etablierten Envelope gelesen:
   - `options.capabilities.deep_mode.requested`
   - `options.capabilities.deep_mode.profile`
   - `options.capabilities.deep_mode.max_budget_tokens`
   - `options.entitlements.deep_mode.allowed`
   - `options.entitlements.deep_mode.quota_remaining`
3. Fehlende Keys bleiben non-breaking und führen zum Basispfad.

### Domain-/Response-Ebene

- Basisergebnis bleibt unter `result.data` (bestehender grouped Response Contract).
- Deep-Status wird ausschließlich additiv unter `result.status.capabilities.deep_mode`
  und `result.status.entitlements.deep_mode` gespiegelt.
- Bei Deep-Fallback darf **kein** Basisergebnis verworfen werden.

## Zielarchitektur (logisch)

```
/analyze request
  -> Stage A: baseline pipeline (deterministic, always required)
  -> Stage B: deep eligibility gate (requested + entitled + budget + quota)
  -> Stage C: optional deep enrichment pipeline (bounded)
  -> Stage D: response projection + status envelope + telemetry flush
```

## Ausführungssequenz (v1)

### Implementierungsstand (#472)

Stand Runtime-Orchestrator (`src/api/web_service.py`, BL-30.3.wp2.r1):

- Der Analyze-Flow projiziert Deep-Mode-Status jetzt deterministisch nach `result.status.capabilities.deep_mode` und
  `result.status.entitlements.deep_mode`.
- Gate-Reihenfolge ist umgesetzt als: `requested` → `profile/policy` → `allowed` → `quota_remaining` → Zeitbudget.
- Budgetaufteilung wird pro Request aus `timeout_seconds` berechnet (`total_request_budget_ms`,
  `baseline_reserved_ms`, `deep_budget_ms`) und über ENV-Parameter feinjustierbar gehalten.
- Bei erfülltem Gate wird `effective=true` und `quota_consumed=1` gesetzt; bei nicht erfülltem Gate bleibt der
  Basispfad aktiv und `fallback_reason` wird gesetzt (`not_entitled`, `quota_exhausted`, `timeout_budget`,
  `policy_guard`).

### Stage A — Baseline first (Pflicht)

- Führt bestehende Analysepfade aus (Address/Context/Suitability/Explainability-Basis).
- Liefert den minimalen stabilen Response-Contract, unabhängig vom Deep-Mode.
- Erzeugt `baseline_completed=true` als interne Laufmarke.

### Stage B — Eligibility Gate

Deep-Mode wird nur aktiviert, wenn **alle** Bedingungen erfüllt sind:

1. `requested == true`
2. `entitlements.allowed == true`
3. `quota_remaining > 0` (wenn Feld vorhanden)
4. Verfügbares Restzeitbudget >= `DEEP_MIN_BUDGET_MS`
5. Policy-Guard nicht verletzt (z. B. `profile` unbekannt)

Wenn eine Bedingung fehlschlägt: Basisergebnis bleibt gültig, Deep wird deaktiviert,
`fallback_reason` wird gesetzt.

### Stage C — Deep Enrichment (optional, bounded)

- Start nur nach erfolgreich abgeschlossenem Basispfad.
- Deep-Runtime erhält ein eigenes Budgetfenster (`deep_budget_ms`, `deep_budget_tokens`),
  das nie den Basispfad rückwirkend blockiert.
- Ergebnisse werden additiv in `result.data` integriert (nur additive Felder/Module).

### Stage D — Projection + Telemetry

- Statusfelder deterministisch setzen (`requested`, `effective`, `fallback_reason`, Quota-Felder).
- Laufzeit- und Budgetmetrik in strukturierte Logs schreiben.
- Response ausliefern, auch wenn Deep fehlgeschlagen/abgebrochen ist.

## Laufzeit-/Kosten-Guardrails (v1)

## 1) Zeitbudget

Empfohlene Budget-Aufteilung pro Request:

- `total_request_budget_ms`: aus API-Timeout (`timeout_seconds`) oder Serverdefault
- `baseline_reserved_ms`: harter Mindestanteil für Basispfad
- `deep_budget_ms = max(0, total - baseline_reserved_ms - safety_margin_ms)`

Regeln:

- Deep startet nur bei `deep_budget_ms >= DEEP_MIN_BUDGET_MS`
- Bei Restzeit < `DEEP_ABORT_THRESHOLD_MS` wird Deep soft-aborted
- Basispfad darf nicht zugunsten von Deep gekürzt werden

## 2) Token-/Kostenbudget

- Client-Wunsch `max_budget_tokens` wird serverseitig geclamped (`0..DEEP_MAX_TOKENS_SERVER`).
- Zusätzlich kann ein profilspezifisches Limit greifen (`profile_cap_tokens`).
- Effektives Budget: `deep_budget_tokens_effective = min(client_cap, profile_cap, server_cap)`.

## 3) Retry-/Abort-Regeln

Retry nur für klar transient markierte Fehler (z. B. 429/5xx/timeout) und nur innerhalb des Budgets:

- `max_retries_per_step = 1`
- exponentieller Backoff mit Jitter, aber begrenzt durch Restbudget
- kein Retry bei Policy-/Validation-Fehlern (`4xx` semantisch, invalid profile, not_entitled)

Abort-Kriterien:

- Restzeit unterschreitet `DEEP_ABORT_THRESHOLD_MS`
- budget tokens erschöpft
- kritischer Guard verletzt (invalid profile/prompt policy)

Bei Abort gilt: `effective=false` nur wenn kein verwertbares Deep-Ergebnis produziert wurde,
andernfalls `effective=true` mit partiellem Deep-Hinweis in Telemetrie.

## Trennung Baseline vs. Deep-Enrichment

| Aspekt | Baseline | Deep-Enrichment |
|---|---|---|
| Pflicht für erfolgreiche Antwort | Ja | Nein |
| Contract-Stabilität | `stable` | zunächst `beta` |
| Timeout-Priorität | Höchste Priorität | Restbudget-basiert |
| Fehlerwirkung | kann Request scheitern lassen | darf auf Basisergebnis zurückfallen |
| Telemetrie | Standard Request-Lifecycle | zusätzliche Deep-spezifische Events |

## Telemetrie-/Tracing-Anforderungen (Mindeststandard)

### Pflicht-Events (strukturierte Logs)

- `api.deep_mode.gate_evaluated`
- `api.deep_mode.execution.start`
- `api.deep_mode.execution.retry`
- `api.deep_mode.execution.abort`
- `api.deep_mode.execution.end`

### Pflichtfelder je Event

- `request_id`, `event`, `ts` (UTC-ISO8601)
- `deep_requested`, `deep_effective`, `deep_profile`
- `deep_budget_ms`, `deep_budget_tokens_effective`
- `duration_ms` (für End-/Abort-Event)
- `fallback_reason` (falls gesetzt)
- `retry_count`

### Integrationsregel zu BL-340 Logging Schema v1

- Event-Payloads müssen das bestehende Redaction-/Schema-Regelwerk aus
  `docs/LOGGING_SCHEMA_V1.md` einhalten.
- Keine Prompt-Rohtexte oder Secrets im Klartext loggen.

### Implementierungsstand (#473)

Stand Telemetrie-/Trace-Härtung (`src/api/web_service.py`, BL-30.3.wp2.r2):

- Deep-Mode emittiert jetzt strukturierte Gate-/Execution-Events unter
  `api.deep_mode.gate_evaluated`, `api.deep_mode.execution.start`,
  `api.deep_mode.execution.retry`, `api.deep_mode.execution.abort`,
  `api.deep_mode.execution.end`.
- Pflichtfelder (`deep_requested`, `deep_effective`, `deep_profile`,
  `deep_budget_ms`, `deep_budget_tokens_effective`, `retry_count`) werden pro Event
  konsistent gesetzt; `duration_ms` wird für `execution.end`/`execution.abort` geführt.
- Operatives Nachweis-Runbook inkl. Beispiel-JSONL liegt unter
  `docs/testing/DEEP_MODE_TRACE_EVIDENCE_RUNBOOK.md`.

## Fallback-/Status-Matrix (Laufzeit)

| Situation | `effective` | `fallback_reason` | Response-Verhalten |
|---|---:|---|---|
| Deep nicht angefordert | false | _(leer)_ | Basisergebnis |
| Nicht entitled | false | `not_entitled` | Basisergebnis |
| Quota erschöpft | false | `quota_exhausted` | Basisergebnis |
| Budget zu klein | false | `timeout_budget` | Basisergebnis |
| Policy-Guard verletzt | false | `policy_guard` | Basisergebnis |
| Deep erfolgreich | true | _(leer)_ | Basisergebnis + Deep-Erweiterung |
| Deep transient fehlgeschlagen nach Retry | false | `runtime_error` | Basisergebnis |

## Risiken / offene Punkte

1. **Quota-Quelle nicht final definiert** (synchron vs. eventual-consistent Entitlement-Store).
2. **Prompt-/Provider-Varianz** kann Laufzeitbudgets sprengen, falls Profile zu breit definiert sind.
3. **Partielle Deep-Ergebnisse** brauchen klare Produktkommunikation (UI/API), um Fehlinterpretation zu vermeiden.
4. **Observability-Drift** möglich, wenn Deep-Events ohne Schema-Guard ergänzt werden.

## Follow-up-Issues

- #470 — Add-on-/Quota-Hypothesen + Transparenzrahmen (Produkt-/GTM-Policy), siehe [`docs/DEEP_MODE_ADDON_QUOTA_HYPOTHESES_V1.md`](../DEEP_MODE_ADDON_QUOTA_HYPOTHESES_V1.md)
- #472 — ✅ BL-30.3.wp2.r1 Runtime-Orchestrator-Implementierung (Gate/Budget/Fallback in `/analyze`) abgeschlossen
- #473 — ✅ BL-30.3.wp2.r2 Deep-Mode-Telemetrie + Trace-Evidence-Runbook abgeschlossen

## DoD-Checklist #469 (Status)

- [x] Technisches Design-Dokument mit Sequenz + Guardrails liegt vor
- [x] Schnittstellen zum bestehenden Analyze-Flow sind benannt
- [x] Risiken/Offene Punkte als Follow-ups erfasst
