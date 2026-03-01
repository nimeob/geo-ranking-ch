> **Diese Datei wurde konsolidiert.** Aktuelle kanonische Version: [entitlements-v1.md](entitlements-v1.md)

---

# BL-30.2.wp2 — Checkout-/Lifecycle-Contract + idempotenter Entitlement-Sync v1

Stand: 2026-03-01  
Issue: #466 (Parent #106, BL-30 Parent #128)

## Ziel

Einen deterministischen Checkout-/Subscription-Lifecycle-Contract festlegen, der Entitlements konsistent aktualisiert und API-Key-Provisioning/Rotation idempotent auslöst.

## Plan-/Produkt-Mapping (Free/Pro/Business)

| Plan-Tier | Produkt-/Preis-Referenz (provider-neutral) | Entitlement-Delta | API-Key-Policy |
| --- | --- | --- | --- |
| `free` | `catalog.free.v1` | `requests.monthly=250`, `rate_limit=5/min`, `trace.debug=no` | Bestehender Key bleibt gültig, keine Rotation erzwungen |
| `pro` | `catalog.pro.v1` | `requests.monthly=5000`, `rate_limit=60/min`, `trace.debug=optional` | Key darf weiterlaufen; Rotation optional bei Security-Flag |
| `business` | `catalog.business.v1` | `requests.monthly=50000`, `rate_limit=240/min`, `trace.debug=yes` | Key-Rotation bei Plan-Wechsel empfohlen (`grace window`) |

## Lifecycle-Events (normativ)

Provider-Webhook-Ereignisse werden intern auf ein kanonisches Event-Modell abgebildet:

| Provider-Ereignis (Beispiel) | Internes Event | Entitlement-Aktion | Key-Aktion |
| --- | --- | --- | --- |
| `checkout.session.completed` | `billing.subscription.created` | Zielplan aktivieren, Zähler initialisieren | Key provisionieren, falls kein aktiver Key vorhanden |
| `customer.subscription.updated` (upgrade) | `billing.subscription.upgraded` | Limits atomar auf Zielplan erhöhen | Optional rotieren; alter Key mit kurzer Grace-Phase |
| `customer.subscription.updated` (downgrade) | `billing.subscription.downgraded` | Limits auf Zielplan reduzieren, Overages markieren | Key bleibt gültig; zusätzliche Scope-Claims entfernen |
| `customer.subscription.deleted` | `billing.subscription.canceled` | Fallback auf `free` + reduzierte Capabilities | Optional sofortige Rotation/Revoke je Policy |
| `invoice.payment_failed` | `billing.payment.failed` | Kein harter Contract-Bruch; Retry-/Grace-Status setzen | Kein sofortiger Revoke ohne explizite Policy |

## Idempotenz- und Reihenfolgeregeln

1. **Idempotency-Key** je Event: `provider:<provider_name>:event_id:<id>`.
2. **Dedup-Store Pflicht**: bereits verarbeitete Event-IDs werden mit `processed_at`, `result_hash` und `plan_tier_after` persistiert.
3. **Out-of-order Schutz**: ältere Event-Versionen (niedriger `event_created_at`) dürfen keinen neueren Zustand überschreiben.
4. **At-least-once-safe**: Wiederholte Webhook-Zustellung führt zu identischem Endzustand (kein doppeltes Quota-Debit, keine doppelte Key-Erzeugung).

## API-Key-Provisioning/Rotation (Folgeregeln)

- **Provisioning-Trigger:** erstmaliges Upgrade auf bezahlten Plan oder fehlender aktiver Key bei `subscription.created`.
- **Rotation-Trigger:** optional bei `upgraded`/`canceled`, verpflichtend bei Security-Incident.
- **Retry-Policy:** exponentielles Backoff (z. B. 1m/5m/15m), max. 3 Versuche; danach `billing.key_sync_pending` markieren.
- **Compensation:** Wenn Key-Operation fehlschlägt, bleibt Entitlement-Update bestehen, aber Status zeigt `provisioning_state=degraded` mit Operability-Hinweis.

## Event-/Contract-Auswirkungen auf API/UI

### API (additiv)
- `result.status.billing.lifecycle_state` (`active|grace|past_due|canceled`)
- `result.status.billing.plan_tier`
- `result.status.entitlements.last_synced_at`
- `result.status.entitlements.sync_source` (`webhook|manual|replay`)

### UI (additiv)
- Billing-Status/Plananzeige aus `result.status.billing.*`.
- Grace-/Payment-Failure-Hinweise ohne Contract-Bruch des Analyze-Basispfads.
- Kein UI-exklusiver Sonder-Endpoint; bestehender API-first Pfad bleibt führend.

## Guardrails (BL-20 Forward-Compatibility)

Verbindliche Referenzen:
- #6 (Forward-Compatibility, kein Rebuild)
- #127 (Capability-/Entitlement-Bridge)
- `docs/BL30_REBUILD_VS_AUSBAU_GUARDRAILS_API_FIRST_V1.md`:
  - `BL30_API_FIRST_NO_BREAKING_CHANGES`
  - `BL30_ENTITLEMENT_SCHEMA_ADDITIVE_ONLY`
  - `BL30_CHECKOUT_IDEMPOTENCY_REQUIRED`
  - `BL30_RUNTIME_FALLBACK_TO_STANDARD`

## Reproduzierbarer Test-/Doku-Nachweisplan

```bash
./.venv-test/bin/python -m pytest -q \
  tests/test_bl30_checkout_lifecycle_contract_docs.py \
  tests/test_bl30_entitlement_contract_docs.py \
  tests/test_api_contract_v1.py \
  tests/test_contract_compatibility_regression.py

./.venv-test/bin/python -m pytest -q tests/test_markdown_links.py
```

## Next Step

- Parent-Sync in #106 und #128 abschließen (Checklist + Closeout für BL-30.2-Later-Track).
