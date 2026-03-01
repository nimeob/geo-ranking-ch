> **Diese Datei wurde konsolidiert.** Aktuelle kanonische Version: [deep-mode-v1.md](deep-mode-v1.md)

---

# BL-30.3.wp1 — Deep-Mode-Contract v1 (Request/Status/Fallback)

Stand: 2026-03-01  
Issue: #468 (Parent #107)

## Ziel

Für BL-30.3 einen **additiven, non-breaking Contract-Rahmen** definieren, damit ein optionaler Deep-Mode
pro Analyze-Request eingeführt werden kann, ohne Legacy-Integrationen zu brechen.

## Contract-Prinzipien (v1)

1. Deep-Mode nutzt den bestehenden Envelope aus BL-20.1.h:
   - Request: `options.capabilities`, `options.entitlements`
   - Response: `result.status.capabilities`, `result.status.entitlements`
2. Kein Pflichtfeld für Legacy-Clients.
3. Bei fehlendem Entitlement oder Quota-Exhaust: **graceful downgrade** auf Basis-Ausführung.
4. Envelope-Struktur bleibt `stable`; produktnahe Deep-Mode-Keys bleiben zunächst `beta`.

## Request-Handshake (additiv)

Empfohlene (optionale) Schlüssel innerhalb des bestehenden Envelopes:

| Pfad | Typ | Stabilität | Bedeutung |
|---|---|---|---|
| `options.capabilities.deep_mode.requested` | `boolean` | `beta` | Client fordert Deep-Mode aktiv an (`true`) oder lässt Basispfad laufen (`false`/fehlend). |
| `options.capabilities.deep_mode.profile` | `string` | `beta` | Gewünschtes Deep-Profil, z. B. `analysis_plus` oder `risk_plus`. |
| `options.capabilities.deep_mode.max_budget_tokens` | `integer` | `beta` | Optionales Upper-Bound-Budget aus Clientsicht (defensiv, serverseitig clampbar). |
| `options.entitlements.deep_mode.allowed` | `boolean` | `beta` | Hinweis, ob laut Upstream-Produktlogik Deep-Mode grundsätzlich freigeschaltet ist. |
| `options.entitlements.deep_mode.quota_remaining` | `integer` | `beta` | Optionaler Stand verfügbarer Deep-Runs/Units vor der Ausführung. |

Hinweis: Da `options.capabilities`/`options.entitlements` bereits als offene Objekte modelliert sind,
bleibt der v1-Request-Contract ohne Schema-Bruch erweiterbar.

## Response-/Status-Semantik (additiv)

Empfohlene Felder im Status-Envelope:

| Pfad | Typ | Stabilität | Bedeutung |
|---|---|---|---|
| `result.status.capabilities.deep_mode.requested` | `boolean` | `beta` | Echo des Requests (normiert). |
| `result.status.capabilities.deep_mode.effective` | `boolean` | `beta` | Ob Deep-Mode im Run tatsächlich aktiv war. |
| `result.status.capabilities.deep_mode.fallback_reason` | `string` | `beta` | Grund bei Downgrade (`not_entitled`, `quota_exhausted`, `timeout_budget`, `policy_guard`). |
| `result.status.entitlements.deep_mode.allowed` | `boolean` | `beta` | Effektive Freigabe im Lauf. |
| `result.status.entitlements.deep_mode.quota_consumed` | `integer` | `beta` | Verbrauchte Quota-Einheiten im Run (typisch `0` oder `1`). |
| `result.status.entitlements.deep_mode.quota_remaining` | `integer` | `beta` | Restquota nach Verarbeitung (falls verfügbar). |

## Deterministische Fallback-Matrix

| Requested | Entitled | Quota verfügbar | Effektiver Modus | Erwartetes Status-Signal |
|---:|---:|---:|---|---|
| `false`/fehlend | beliebig | beliebig | Basis | `effective=false`, kein Fehler |
| `true` | `false` | beliebig | Basis | `effective=false`, `fallback_reason=not_entitled` |
| `true` | `true` | `0` | Basis | `effective=false`, `fallback_reason=quota_exhausted` |
| `true` | `true` | `>0` | Deep | `effective=true`, `quota_consumed>=1` |

## Beispiel (Request)

```json
{
  "request_id": "req-demo-001",
  "input": {"mode": "address", "address": "Bahnhofstrasse 1, Zürich"},
  "requested_modules": ["building_profile", "context_profile", "suitability_light", "explainability"],
  "options": {
    "response_mode": "compact",
    "capabilities": {
      "deep_mode": {
        "requested": true,
        "profile": "analysis_plus",
        "max_budget_tokens": 12000
      }
    },
    "entitlements": {
      "deep_mode": {
        "allowed": true,
        "quota_remaining": 14
      }
    }
  }
}
```

## Beispiel (Response-Status bei Downgrade)

```json
{
  "ok": true,
  "request_id": "req-demo-001",
  "result": {
    "status": {
      "capabilities": {
        "deep_mode": {
          "requested": true,
          "effective": false,
          "fallback_reason": "quota_exhausted"
        }
      },
      "entitlements": {
        "deep_mode": {
          "allowed": true,
          "quota_consumed": 0,
          "quota_remaining": 0
        }
      }
    }
  }
}
```

## Guardrails / Nicht-Ziele (wp1)

- Keine sofortige Runtime-Durchsetzung in API/UI in diesem Work-Package.
- Keine finalen Pricing-Entscheide (Folgearbeit in #470).
- Keine Prompt-/Orchestrierungs-Implementierung (Folgearbeit in #469).

## Anschluss-Folgearbeiten

- #469: Deep-Mode-Orchestrierung + Runtime-Guardrails (Design abgeschlossen, siehe `docs/api/deep-mode-orchestration-guardrails-v1.md`)
- #470: Add-on-/Quota-Hypothesen + Transparenzrahmen (Produkt-/GTM-Pfad), umgesetzt in [`docs/DEEP_MODE_ADDON_QUOTA_HYPOTHESES_V1.md`](../DEEP_MODE_ADDON_QUOTA_HYPOTHESES_V1.md)
- #472: ✅ Runtime-Orchestrator im `/analyze`-Flow implementiert (Gate/Budget/Fallback in `src/api/web_service.py`)
- #473: Deep-Mode-Telemetrie + Trace-Evidence absichern
