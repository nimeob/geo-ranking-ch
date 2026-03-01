# Deep-Mode — Konsolidierte Dokumentation v1

> Dieses Dokument ist der **kanonische Ort** für Deep-Mode-Contract und Orchestrierungs-Guardrails.
> Quell-Dokumente bleiben für Test-Kompatibilität erhalten.

Stand: 2026-03-01

**Quell-Dokumente:**
- [`docs/api/deep-mode-contract-v1.md`](deep-mode-contract-v1.md) — Contract/Request/Status/Fallback (#468)
- [`docs/api/deep-mode-orchestration-guardrails-v1.md`](deep-mode-orchestration-guardrails-v1.md) — Orchestrierung/Guardrails (#469)

---

## 1) Contract-Prinzipien (v1)

1. Deep-Mode nutzt den bestehenden Envelope aus BL-20.1.h (`options.capabilities`, `options.entitlements`)
2. Kein Pflichtfeld für Legacy-Clients
3. Bei fehlendem Entitlement oder Quota-Exhaust: **graceful downgrade** auf Basis-Ausführung
4. Envelope-Struktur: `stable`; Deep-Mode-Keys: `beta`

---

## 2) API-Felder (Request/Response)

### Request (additiv, alle optional)

| Pfad | Typ | Bedeutung |
|---|---|---|
| `options.capabilities.deep_mode.requested` | boolean | Client fordert Deep-Mode an |
| `options.capabilities.deep_mode.profile` | string | Gewünschtes Profil (`analysis_plus`, `risk_plus`) |
| `options.capabilities.deep_mode.max_budget_tokens` | integer | Upper-Bound-Budget (serverseitig clampbar) |
| `options.entitlements.deep_mode.allowed` | boolean | Deep-Mode grundsätzlich freigeschaltet |
| `options.entitlements.deep_mode.quota_remaining` | integer | Verfügbare Deep-Runs vor Ausführung |

### Response (additiv)

| Pfad | Typ | Bedeutung |
|---|---|---|
| `result.status.capabilities.deep_mode.requested` | boolean | Echo des Requests |
| `result.status.capabilities.deep_mode.effective` | boolean | Ob Deep-Mode tatsächlich aktiv war |
| `result.status.capabilities.deep_mode.fallback_reason` | string | Grund bei Downgrade |
| `result.status.entitlements.deep_mode.allowed` | boolean | Effektive Freigabe im Lauf |
| `result.status.entitlements.deep_mode.quota_consumed` | integer | Verbrauchte Quota-Einheiten (0 oder 1) |
| `result.status.entitlements.deep_mode.quota_remaining` | integer | Restquota nach Verarbeitung |

---

## 3) Deterministische Fallback-Matrix

| Requested | Entitled | Quota | Effektiver Modus | Status |
|---|---|---|---|---|
| `false`/fehlend | beliebig | beliebig | Basis | `effective=false`, kein Fehler |
| `true` | `false` | beliebig | Basis | `effective=false`, `fallback_reason=not_entitled` |
| `true` | `true` | `0` | Basis | `effective=false`, `fallback_reason=quota_exhausted` |
| `true` | `true` | `>0` | Deep | `effective=true`, `quota_consumed>=1` |

**Fallback-Reasons:** `not_entitled | quota_exhausted | timeout_budget | policy_guard | runtime_error`

**Keine Unterdrückung des Basisergebnisses** bei Deep-Fallback.

---

## 4) Zielarchitektur (Orchestrierung)

```
/analyze request
  -> Stage A: baseline pipeline (deterministisch, immer erforderlich)
  -> Stage B: deep eligibility gate (requested + entitled + budget + quota)
  -> Stage C: optional deep enrichment pipeline (budgetiert)
  -> Stage D: response projection + status envelope + telemetry flush
```

### Eligibility-Gate-Reihenfolge
1. `requested == true`
2. `profile/policy` check
3. `allowed == true`
4. `quota_remaining > 0`
5. Zeitbudget verfügbar

### Budgetaufteilung (ENV-Parameter)
Aus `timeout_seconds` abgeleitet: `total_request_budget_ms`, `baseline_reserved_ms`, `deep_budget_ms`.

---

## 5) Quota-Policy-Rahmen (Hypothesen v1)

*Vollständig: [`docs/DEEP_MODE_ADDON_QUOTA_HYPOTHESES_V1.md`](../DEEP_MODE_ADDON_QUOTA_HYPOTHESES_V1.md)*

- **Unit:** 1 Deep-Run = 1 Quota-Unit; Basispfad = 0
- **Reset-Fenster:** monatlich (aligned mit Tier-Logik)
- **Graceful-Downgrade:** bei `allowed=false` oder `quota_remaining=0` bleibt Basisergebnis verpflichtend erhalten
- **No Surprise Rule:** `fallback_reason` muss immer gesetzt sein

---

## 6) Telemetrie-Mindestanforderungen

Pro Deep-Lauf im strukturierten Log:
- `request_id`, `deep_mode.effective`, `deep_mode.profile`, `deep_mode.fallback_reason`
- `timing_ms.total`, `timing_ms.baseline`, `timing_ms.deep`
- `quota_consumed`, `error_code` (falls vorhanden)

---

## 7) Guardrails (BL-30/BL-20 Forward-Compatibility)

Pflichtmarker aus [`docs/BL30_REBUILD_VS_AUSBAU_GUARDRAILS_API_FIRST_V1.md`](../BL30_REBUILD_VS_AUSBAU_GUARDRAILS_API_FIRST_V1.md):
- `BL30_API_FIRST_NO_BREAKING_CHANGES`
- `BL30_RUNTIME_FALLBACK_TO_STANDARD`

Deep-Mode-spezifisch:
- Baseline first — Deep nie vor Basis-Ergebnis
- Kein Hard-Fail bei Deep-Ausfall (immer Basisergebnis)
- Kein Runtime-Abhängigkeit auf Deep für Standard-Clients

---

## 8) Follow-up-Tracks

- ✅ #468 Contract v1
- ✅ #469 Orchestrierungs-Guardrails
- ✅ #470 Add-on/Quota-Hypothesen
- 🔲 #472 Runtime-Orchestrator implementieren
- 🔲 #473 Deep-Mode-Telemetrie + Trace-Evidence absichern
