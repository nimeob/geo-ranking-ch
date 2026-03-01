# Usage/Metering v1 — Events, Rollups, Limits

Stand: 2026-03-01  
Issue: #629 (Parent: #577)

> **Ziel:** Ein v1-Usage-/Metering-Design, das Quotas/Limits und Billing-/Entitlement-Entscheide **deterministisch**
> und **idempotent** abstützt – ohne sich früh auf einen Billing-Provider festzulegen.

## 0) Kanonische Referenzen (nicht duplizieren)

- Entitlements/Capabilities (Kanonisch + Gate-Katalog): [`docs/api/entitlements-v1.md`](api/entitlements-v1.md)
- Entitlements (Ergänzung/Parallelisierungs-Doc): [`docs/ENTITLEMENTS_v1.md`](ENTITLEMENTS_v1.md) (Issue #627)
- Billing-/Subscription-Lifecycle: [`docs/BILLING_LIFECYCLE_v1.md`](BILLING_LIFECYCLE_v1.md) (Issue #628)

## 1) Begriffe (v1)

- **Usage**: gemessene Nutzung im System (Events + Aggregationen).
- **Metering**: Mess-/Erfassungs-Mechanik (was, wann, wie; inkl. Idempotenz/Dedupe).
- **Quota/Limit**: normative Obergrenze aus Entitlements (z. B. `entitlement.requests.monthly`).
- **Rollup**: Aggregation von Raw-Events in Zeitfenster (daily/monthly) zur schnellen Auswertung.

> Abgrenzung: **Rate-Limits** (Burst/Requests pro Zeit) sind primär Edge/WAF/The API.
> **Usage-/Quota-Limits** sind primär Billing-/Entitlement-getrieben und beziehen sich typischerweise auf
> Monats-/Tagesfenster.

## 2) No-regrets Defaults (Design-Prinzipien)

1. **Org-first**: v1 zählt Usage primär auf **Org-Scope** (Tenant).
2. **Idempotent & out-of-order safe**: Usage-Events müssen deduplizierbar sein (z. B. über `request_id`).
3. **Append-only Events** + **derivierte Rollups**: Events sind die Quelle; Rollups sind ableitbar/backfillbar.
4. **Fail-safe Enforcement**: Wenn Usage nicht sicher auswertbar ist, gilt ein konservativer Fallback
   (z. B. `quota_unknown` → deny oder degrade; Entscheidung hängt von Kosten-/Fraud-Risiko ab).
5. **Provider-neutral**: Billing-Provider (Stripe etc.) ist nicht Teil des v1-Metering-Kerns.

## 3) Was wird gemessen? (Metric Catalog v1)

Minimaler, erweiterbarer Katalog (Keys sind stabil, additiv):

### 3.1 Requests
- `requests.analyze` — Jede akzeptierte `/analyze`-Ausführung (sync oder async).
- `requests.analyze.deep_mode` — Deep-Mode-Path (falls aktiviert; optionaler Sub-Metric).

### 3.2 Compute-/Budget-Nähe (optional v1, aber vorgesehen)
- `runtime_seconds.analyze` — wall-clock runtime (gerundet/gebinned).
- `tokens.deep_mode` — Tokenverbrauch (nur falls LLM-Usage relevant ist).

### 3.3 Data/Export (optional)
- `exports.rows` — Anzahl exportierter Datensätze.

> Wichtig: Der Katalog ist **nicht** die Entitlement-Liste.
> Entitlements referenzieren Metric-Keys indirekt (z. B. `entitlement.requests.monthly` → `requests.analyze`).

## 4) Granularität & Scopes (Org/User/API-Key)

### 4.1 Scopes
- **Org** (Default, v1): Billing-/Monetization-Anker.
- **API-Key** (optional v1+): nützlich für differenzierte Policies oder Debugging.
- **User** (optional v1+): Seats/Role-Limits, später.

### 4.2 No-regrets Regel v1
- Events tragen **org_id** immer.
- `api_key_id`/`user_id` sind optional und dürfen `null` sein.
- Rollups werden primär pro `org_id` geführt; optionale secondary rollups können später ergänzt werden.

## 5) Event-Schema v1 (usage_event)

### 5.1 Normatives JSON-Schema (konzeptuell)

```json
{
  "event_id": "usev_01J...",
  "idempotency_key": "request_id:req-3e5f0a1f0a87419d",
  "occurred_at_utc": "2026-03-01T21:20:12.123456Z",

  "org_id": "org_123",
  "user_id": "user_456",
  "api_key_id": "ak_789",

  "metric_key": "requests.analyze",
  "quantity": 1,
  "unit": "count",

  "attributes": {
    "route": "/analyze",
    "mode": "extended",
    "async": false,
    "request_id": "req-3e5f0a1f0a87419d",
    "source": "api"
  }
}
```

### 5.2 Idempotenz/Dedupe (verbindlich)

- **Dedup-Key v1:** `idempotency_key` ist Pflicht und muss pro „zählbarer Aktion“ stabil sein.
- No-regrets Default:
  - `idempotency_key = "request_id:<request_id>"` für `/analyze`-Requests.
  - Für Async kann zusätzlich der `job_id` verwendet werden:
    - `"job_id:<job_id>"` für *job-level* events
    - `"request_id:<request_id>"` für *request-level* acceptance

**Regel:** Doppelt zugestellte Requests (Retries) dürfen **nicht** doppelt zählen.

### 5.3 Minimaler SQL-Sketch (optional, als Design-Target)

- `usage_events` (append-only)
  - Unique: `(org_id, idempotency_key)` oder `(idempotency_key)` global (je nach Key-Design)
  - Index: `(org_id, occurred_at_utc)`, `(org_id, metric_key, occurred_at_utc)`

## 6) Rollups (Daily/Monthly) + Retention

### 6.1 Rollup-Model (v1)

- **Daily Rollup**: `usage_rollups_daily`
  - Key: `(org_id, metric_key, day_utc)`
  - Value: `sum_quantity`
- **Monthly Rollup**: `usage_rollups_monthly`
  - Key: `(org_id, metric_key, month_utc)`
  - Value: `sum_quantity`

> No-regrets: Monthly kann aus Daily aggregiert werden; Daily ist das praktischere Backfill-Granulat.

### 6.2 Rollup-Strategie

- Rollups können synchron (im Request-Pfad) oder async (Worker) erfolgen.
- v1-Empfehlung:
  1) **Event write** im Request-Pfad (idempotent, schnell)
  2) Rollup async (eventual consistency), mit optionalem „read-your-writes“ im Limit-Check

### 6.3 Retention (Richtwerte, v1)

- `usage_events` (raw): **14–30 Tage** (Debug/Abrechnungsklärung; abhängig von Speicher-/Privacy-Policy).
- `usage_rollups_daily`: **13 Monate** (Monatsfenster + Audit).
- `usage_rollups_monthly`: **24 Monate** (Reporting; optional).

## 7) Limits: Hard vs Soft + Enforcement-Orte

### 7.1 Limit-Typen

- **Hard limit**: bei Überschreitung wird Request/Job abgewiesen (`quota_exhausted`).
- **Soft limit**: Request läuft weiter, aber UI/Status zeigt Overage/Warning (z. B. für Grace).

### 7.2 Enforcement-Orte (v1)

- **API Layer (SSOT):** entscheidet `allow/deny` vor kostenrelevanter Ausführung.
- **Worker/Async:** muss ebenfalls enforce’n (insbesondere bei Jobs, die später weiterlaufen könnten).

### 7.3 Kopplung an Entitlements

- Entitlements liefern die Norm (z. B. `entitlement.requests.monthly`).
- Metering liefert den Ist-Stand (z. B. `usage_rollups_monthly.requests.analyze`).
- Die Entscheidung ist „konservativ“:
  - Wenn Usage nicht zuverlässig lesbar ist → `allowed=false` oder degrade (abhängig vom Risiko).

## 8) End-to-End Beispiel (Event → Rollup → Limit Check)

### Szenario
- Org hat Entitlement: `entitlement.requests.monthly = 5000`.
- Aktueller Monat: `usage_rollups_monthly.requests.analyze = 4999`.
- Neuer Request kommt rein (`request_id=req-...`).

### Ablauf (v1, idealisiert)

1) API erhält Request
2) API schreibt idempotent Usage-Event:
   - `metric_key=requests.analyze`, `quantity=1`, `idempotency_key=request_id:req-...`
3) Limit-Check:
   - liest `monthly_count` (Rollup; optional +1 wenn Event gerade geschrieben wurde)
   - berechnet `remaining = 5000 - monthly_count`
4) Entscheidung:
   - falls `remaining <= 0` → `deny` (`quota_exhausted`)
   - sonst `allow` und Ausführung startet

### Pseudocode (sketch)

```python
ent = get_entitlements(org_id)
quota = int(ent.get("entitlement.requests.monthly", 0))

# 1) Metering write (idempotent)
write_usage_event(
    org_id=org_id,
    metric_key="requests.analyze",
    quantity=1,
    idempotency_key=f"request_id:{request_id}",
)

# 2) Read rollup (eventual consistency ok; optional read-your-writes)
count = read_monthly_rollup(org_id, metric_key="requests.analyze", month=utc_month_now())

remaining = max(0, quota - count)
if remaining <= 0:
    return deny("quota_exhausted")
return allow()
```

## 9) Abhängigkeiten / Cross-Links

- Entitlement-Modell & Evaluation (Issue #627): [`docs/ENTITLEMENTS_v1.md`](ENTITLEMENTS_v1.md)
- Billing-/Lifecycle (Issue #628): [`docs/BILLING_LIFECYCLE_v1.md`](BILLING_LIFECYCLE_v1.md)

## 10) Offene Trade-offs (bewusst v1)

- Wo genau liegt der Rollup-Job (API inline vs. Worker)?
- Conservative fallback policy bei Usage-Read-Fehlern (deny vs. allow+warn) hängt vom Kosten-/Fraud-Profil ab.
- Ob API-Key-scope rollups in v1 nötig sind (Debug/Abuse) oder erst in v1+.
