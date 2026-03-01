# BL-30.2.wp1 — Entitlement-Contract v1 + Gate-Semantik

Stand: 2026-03-01  
Issue: #465 (Parent #106, BL-30 Parent #128)

## Ziel

Für BL-30.2 einen **implementierbaren Entitlement-Contract v1** festlegen, damit Checkout/Lifecycle-Folgearbeit (#466) auf einem klaren, testbaren Gate-Rahmen aufbauen kann.

## Normativer Gate-Katalog v1 (Free/Pro/Business)

Die Gate-Namen sind verbindlich an die BL-30.1-Matrix angebunden (`docs/PRICING_TIER_LIMIT_MATRIX_V1.md`):

| Gate-Key | Typ | Semantik (v1) | Free | Pro | Business |
| --- | --- | --- | --- | --- | --- |
| `entitlement.requests.monthly` | integer | Monatliches Analyze-Kontingent je Tenant/Plan | 250 | 5'000 | 50'000 |
| `entitlement.requests.rate_limit` | string | Kurzfristiges Burst-/Rate-Limit (`<count>/min`) | `5/min` | `60/min` | `240/min` |
| `capability.explainability.level` | enum | Erlaubte Explainability-Tiefe (`basic`,`extended`,`full`) | `basic` | `extended` | `full` |
| `capability.gui.access` | enum | GUI-Zugriffsprofil (`demo`,`full`,`full+workspace`) | `demo` | `full` | `full+workspace` |
| `capability.trace.debug` | enum | Zugriff auf request_id-Trace-Debug (`no`,`optional`,`yes`) | `no` | `optional` | `yes` |

## Runtime-Enforcement-Schnittstellen (API/UI)

### Request-Eingang (additiv)
- `options.entitlements.plan_tier` (`free|pro|business`)
- `options.entitlements.requests.monthly_remaining` (integer, optional)
- `options.entitlements.requests.rate_limit_per_minute` (integer, optional)
- `options.capabilities.explainability.level` (string, optional)
- `options.capabilities.gui.access` (string, optional)
- `options.capabilities.trace.debug` (string, optional)

### Response-/Status-Projektion (additiv)
- `result.status.entitlements.plan_tier`
- `result.status.entitlements.requests.monthly_remaining`
- `result.status.entitlements.requests.rate_limit_per_minute`
- `result.status.capabilities.explainability.level`
- `result.status.capabilities.gui.access`
- `result.status.capabilities.trace.debug`

Hinweis: Alle BL-30.2-Felder bleiben innerhalb des vorhandenen Capability-/Entitlement-Envelopes (`options.*` / `result.status.*`) und sind damit für Legacy-Clients optional.

## Contract-/API-Auswirkungen (additiv, non-breaking)

1. **Keine Breaking Changes an `/analyze`**: bestehende Pflichtfelder bleiben unverändert, neue Entitlement-Signale sind optional.
2. **429-Semantik bleibt kanonisch**: harte Rate-Limit-Verletzungen bleiben über bestehende Fehlercodes (`rate_limited`) aus `docs/api/contract-v1.md` abbildbar.
3. **UI-Feature-Gating nur über Status**: GUI entscheidet nicht über eigene Sonder-Contracts, sondern liest `result.status.capabilities.*`.
4. **Checkout/Lifecycle ist nachgelagert**: #466 darf nur Gate-Werte synchronisieren/aktualisieren, nicht den Analyze-Basispfad ersetzen.

## Guardrails (BL-20 Forward-Compatibility)

Verbindliche Referenzen:
- #6 (Forward-Compatibility, additiver Ausbau statt Rebuild)
- #127 (Capability-/Entitlement-Bridge im Contract)
- `docs/BL30_REBUILD_VS_AUSBAU_GUARDRAILS_API_FIRST_V1.md` (Pflichtmarker):
  - `BL30_API_FIRST_NO_BREAKING_CHANGES`
  - `BL30_ENTITLEMENT_SCHEMA_ADDITIVE_ONLY`
  - `BL30_CHECKOUT_IDEMPOTENCY_REQUIRED`
  - `BL30_RUNTIME_FALLBACK_TO_STANDARD`

## Reproduzierbarer Nachweispfad (Tests/Doku)

```bash
./.venv-test/bin/python -m pytest -q \
  tests/test_bl30_entitlement_contract_docs.py \
  tests/test_api_contract_v1.py \
  tests/test_contract_compatibility_regression.py

./.venv-test/bin/python -m pytest -q tests/test_markdown_links.py
```

## Next Step

- #466 (Checkout-/Lifecycle-Contract + idempotenter Entitlement-Sync) auf Basis dieses Gate-Katalogs umsetzen.
