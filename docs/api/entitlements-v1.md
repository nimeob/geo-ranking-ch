# Entitlements — Konsolidierte Dokumentation v1

> Dieses Dokument ist der **kanonische Ort** für Entitlement, Checkout & Billing-Lifecycle.
> Quell-Dokumente bleiben für Test-Kompatibilität erhalten.

Stand: 2026-03-01

**Quell-Dokumente:**
- [`docs/api/bl30-entitlement-contract-v1.md`](bl30-entitlement-contract-v1.md) — Gate-Semantik (#465)
- [`docs/api/bl30-checkout-lifecycle-contract-v1.md`](bl30-checkout-lifecycle-contract-v1.md) — Checkout/Lifecycle (#466)
- [`docs/api/entitlement-billing-lifecycle-v1.md`](entitlement-billing-lifecycle-v1.md) — Fachlogik (#586)

---

## 1) Kanonischer Gate-Katalog v1 (Free / Pro / Business)

*Referenz: [`docs/PRICING_TIER_LIMIT_MATRIX_V1.md`](../PRICING_TIER_LIMIT_MATRIX_V1.md)*

| Gate-Key | Typ | Free | Pro | Business |
|---|---|---|---|---|
| `entitlement.requests.monthly` | integer | 250 | 5'000 | 50'000 |
| `entitlement.requests.rate_limit` | string | `5/min` | `60/min` | `240/min` |
| `capability.explainability.level` | enum | `basic` | `extended` | `full` |
| `capability.gui.access` | enum | `demo` | `full` | `full+workspace` |
| `capability.trace.debug` | enum | `no` | `optional` | `yes` |

### Prioritätsregel für effektive Auswertung
1. Plan-Baseline
2. aktive org-spezifische Overrides
3. temporäre Lifecycle-Constraints (Grace/Past-Due)

**Bei Konflikten: engste Einschränkung gewinnt (fail-safe).**

---

## 2) API-Contract (Entitlement-Felder)

### Request (additiv)
- `options.entitlements.plan_tier` (`free|pro|business`)
- `options.entitlements.requests.monthly_remaining` (integer, optional)
- `options.entitlements.requests.rate_limit_per_minute` (integer, optional)
- `options.capabilities.explainability.level`
- `options.capabilities.gui.access`
- `options.capabilities.trace.debug`

### Response (additiv)
- `result.status.entitlements.plan_tier`
- `result.status.entitlements.requests.monthly_remaining`
- `result.status.entitlements.requests.rate_limit_per_minute`
- `result.status.capabilities.explainability.level`
- `result.status.capabilities.gui.access`
- `result.status.capabilities.trace.debug`
- `result.status.billing.lifecycle_state` (`active|grace|past_due|canceled|suspended`)
- `result.status.billing.plan_tier`
- `result.status.entitlements.last_synced_at`
- `result.status.entitlements.sync_source` (`webhook|manual|replay`)

**Keine Breaking Changes:** alle neuen Felder sind optional und additiv.

---

## 3) Billing-/Subscription-Lifecycle

### Zustände

| State | Analyze-Verhalten | Entitlement-Wirkung |
|---|---|---|
| `trialing` | normal | Trial-Limits |
| `active` | normal | Plan-Limits |
| `grace` | normal mit Hinweis | Limits optional gedrosselt |
| `past_due` | eingeschränkt möglich | konservativer Fallback |
| `canceled` | weiter im Free-Scope | Rückfall auf Free |
| `suspended` | blockiert | minimale/keine Capabilities |

### Kanonische Lifecycle-Events

| Provider-Ereignis | Internes Event | Entitlement-Aktion |
|---|---|---|
| `checkout.session.completed` | `billing.subscription.created` | Zielplan aktivieren, Zähler initialisieren |
| `subscription.updated` (upgrade) | `billing.subscription.upgraded` | Limits atomar erhöhen |
| `subscription.updated` (downgrade) | `billing.subscription.downgraded` | Limits reduzieren, Overages markieren |
| `subscription.deleted` | `billing.subscription.canceled` | Fallback auf `free` |
| `invoice.payment_failed` | `billing.payment.failed` | Grace-Status setzen, kein sofortiger Revoke |

---

## 4) Idempotenz & Checkout-Regeln

- **Idempotency-Key:** `provider:<provider_name>:event_id:<event_id>`
- **Dedup-Store:** `processed_at`, `state_before/after`, `result_hash`, `status`
- **Out-of-order Schutz:** ältere Events überschreiben keinen neueren Zustand
- **At-least-once-safe:** wiederholte Webhook-Lieferung → identischer Endzustand

### API-Key-Provisioning
- Trigger: erstmaliges Upgrade auf bezahlten Plan oder fehlender aktiver Key
- Rotation: optional bei Upgrade, verpflichtend bei Security-Incident
- Retry: exponentielles Backoff (1m/5m/15m), max. 3 Versuche; danach `provisioning_state=degraded`

---

## 5) Verbindliche Guardrails (BL-30/BL-20 Forward-Compatibility)

Pflichtmarker aus [`docs/BL30_REBUILD_VS_AUSBAU_GUARDRAILS_API_FIRST_V1.md`](../BL30_REBUILD_VS_AUSBAU_GUARDRAILS_API_FIRST_V1.md):
- `BL30_API_FIRST_NO_BREAKING_CHANGES`
- `BL30_ENTITLEMENT_SCHEMA_ADDITIVE_ONLY`
- `BL30_CHECKOUT_IDEMPOTENCY_REQUIRED`
- `BL30_RUNTIME_FALLBACK_TO_STANDARD`

---

## 6) Reproduzierbarer Test-Nachweispfad

```bash
./.venv-test/bin/python -m pytest -q \
  tests/test_bl30_entitlement_contract_docs.py \
  tests/test_bl30_checkout_lifecycle_contract_docs.py \
  tests/test_entitlement_billing_lifecycle_v1_docs.py \
  tests/test_api_contract_v1.py \
  tests/test_contract_compatibility_regression.py
```
