# Entitlement-/Billing-Lifecycle v1 (GTM Follow-up)

Stand: 2026-03-01  
Issue: #586 (Parent #577)

## Ziel des Work-Packages

Dieses Dokument konkretisiert für das GTM→Data-Architecture-Follow-up die
umsetzbare Fachlogik für:

- Capability-/Entitlement-Modell v1
- Billing-/Subscription-Zustände mit klaren Übergangsregeln
- idempotente Webhook-Verarbeitung inkl. Fehlerbehandlung
- Usage-/Metering-Granularität (Org/User/API-Key) und Aggregationslogik

Das Dokument baut auf dem Kernmodell aus
[`docs/GTM_TO_DB_ARCHITECTURE_V1.md`](../GTM_TO_DB_ARCHITECTURE_V1.md) auf und
bleibt additive/non-breaking gegenüber dem bestehenden Analyze-Contract.

## 1) Capability-/Entitlement-Modell v1

### 1.1 Prinzipien

1. **Plan ist Ausgangspunkt, Entitlement ist effektiver Laufzeitwert.**
2. **Entitlements sind tenant-lokal evaluierbar** (keine globalen Side-Channels).
3. **Capabilities und Limits werden technisch gleich behandelt**
   (`key`, `value`, `value_type`, `source`, `effective_from`, `effective_to`).
4. **Overrides sind explizit** (`source=override`) und auditierbar.

### 1.2 Kanonische Entitlement-Schlüssel (v1)

| Key | Typ | Beispielwert | Semantik |
| --- | --- | --- | --- |
| `entitlement.requests.monthly` | integer | `5000` | Monatskontingent pro Org |
| `entitlement.requests.rate_limit` | string | `60/min` | Burst-/Rate-Limit |
| `capability.explainability.level` | enum | `extended` | erlaubte Explainability-Tiefe |
| `capability.gui.access` | enum | `full` | GUI-Zugriffsprofil |
| `capability.trace.debug` | enum | `optional` | request_id-Trace-Zugriff |

Die v1-Schlüssel sind kompatibel mit den BL-30-Vertragsartefakten
([`docs/api/bl30-entitlement-contract-v1.md`](bl30-entitlement-contract-v1.md),
[`docs/api/bl30-checkout-lifecycle-contract-v1.md`](bl30-checkout-lifecycle-contract-v1.md)).

### 1.3 Prioritätsregel für effektive Auswertung

Effektive Entitlements werden deterministisch berechnet:

1. Plan-Baseline (z. B. Free/Pro/Business)
2. aktive org-spezifische Overrides
3. temporäre Lifecycle-Constraints (z. B. Grace-/Past-Due-Dämpfung)

Bei Konflikten gilt: **engste Einschränkung gewinnt** (fail-safe).

## 2) Billing-/Subscription-Zustände und Übergangsregeln

### 2.1 Kanonische Zustände (v1)

| State | Beschreibung | Analyze-Verhalten | Entitlement-Wirkung |
| --- | --- | --- | --- |
| `trialing` | Testphase aktiv | normal | Trial-Limits |
| `active` | regulär bezahlt/aktiv | normal | Plan-Limits |
| `grace` | Zahlungsproblem mit Schonfrist | normal mit Hinweis | Limits optional gedrosselt |
| `past_due` | über Grace hinaus offen | eingeschränkt möglich | konservativer Fallback |
| `canceled` | gekündigt/beendet | weiter möglich im Free-Scope | Rückfall auf Free |
| `suspended` | manuelle Sperre (Compliance/Security) | blockiert/streng limitiert | minimale/keine Capabilities |

### 2.2 Erlaubte Übergänge

| From | Event (kanonisch) | To | Regel |
| --- | --- | --- | --- |
| `trialing` | `billing.subscription.activated` | `active` | nach erfolgreicher Aktivierung |
| `active` | `billing.payment.failed` | `grace` | Grace-Fenster startet |
| `grace` | `billing.payment.recovered` | `active` | Rückkehr ohne Planverlust |
| `grace` | `billing.grace.expired` | `past_due` | ohne Recovery |
| `past_due` | `billing.subscription.canceled` | `canceled` | eindeutiger Endzustand |
| `active` | `billing.subscription.canceled` | `canceled` | Kündigung regulär |
| `*` | `billing.subscription.suspended` | `suspended` | Security/Compliance-Override |
| `suspended` | `billing.subscription.reinstated` | `active`/`grace` | abhängig von Billing-Stand |

**Nicht erlaubte direkte Übergänge** (z. B. `trialing -> past_due` ohne
Zwischenereignis) werden verworfen und als Anomalie protokolliert.

## 3) Idempotente Webhook-Strategie + Fehlerbehandlung

### 3.1 Idempotenzkern

- Dedup-Key: `provider:<provider_name>:event_id:<event_id>`
- Persistierter Verarbeitungsnachweis:
  - `received_at`
  - `processed_at`
  - `state_before` / `state_after`
  - `result_hash`
  - `status` (`processed|duplicate|rejected|failed_retriable|failed_terminal`)

Wird ein identischer Event erneut zugestellt, ist das Ergebnis deterministisch:
**kein doppelter Quota-Write, keine doppelte Key-Rotation, keine doppelte
Audit-Side-Effects**.

### 3.2 Ordering-/Replay-Regeln

1. Event hat kanonische Zeitmarker (`event_created_at`, optional `event_version`).
2. Ältere Events dürfen keinen neueren Zustand überschreiben.
3. Replays sind erlaubt, aber nur read/verify oder no-op, falls bereits verarbeitet.
4. Bei unklarer Reihenfolge: Event in Quarantäne (`status=rejected`) + manueller
   Reconcile-Pfad.

### 3.3 Fehlerbehandlung (v1)

| Fehlerklasse | Beispiel | Behandlung |
| --- | --- | --- |
| `invalid_payload` | Schema verletzt | sofort `rejected`, kein Retry |
| `unknown_subscription` | Referenz fehlt | `failed_retriable`, Retry mit Backoff |
| `transient_store_error` | DB/Lock-Timeout | `failed_retriable`, Retry mit Jitter |
| `forbidden_transition` | nicht erlaubter State-Wechsel | `rejected`, Audit + Alert |
| `side_effect_partial` | Entitlement ok, Key-Rotation fehlgeschlagen | Zustand committen, Follow-up Job `pending_repair` |

Retry-Policy: exponentiell (1m/5m/15m, max. 3), danach terminaler Status +
operativer Alert.

## 4) Usage-/Metering-Modell (Org/User/API-Key)

### 4.1 Granularität und Scope

| scope_type | scope_id | Primärzweck |
| --- | --- | --- |
| `org` | `org_id` | Abrechnungs-/Planlimit (kanonisch) |
| `user` | `user_id` | Fair-Use, Missbrauchserkennung, interne Kostenzuordnung |
| `api_key` | `api_key_id` | technische Drosselung, Incident-Isolation |

Kanonische Abrechnung läuft auf **Org-Ebene**; User/API-Key dienen als
sekundäre Kontroll- und Diagnoseebene.

### 4.2 Aggregationslogik (v1)

1. Write-Pfad erfasst jeden Analyze-Call als Metering-Event mit `org_id` plus
   optional `user_id`/`api_key_id`.
2. Rolling-Minute-Aggregation für Rate-Limits (`rate_limit`).
3. Monatsaggregation pro Org (`requests.monthly`) als Billing-Basis.
4. Reconcile-Job gleicht Summen regelmäßig gegen Roh-Events ab (Drift-Erkennung).

### 4.3 Deterministische Runtime-Auswertung

- Gate 1: `org.monthly_remaining > 0`
- Gate 2: `org.rate_window` innerhalb Limit
- Gate 3 (optional): `api_key.rate_window` innerhalb Key-Limit
- Gate 4 (optional): `user.rate_window` innerhalb Fair-Use-Band

Bei Konflikt gilt immer das restriktivste Gate.

## 5) Non-Goals / offene Risiken

### Non-Goals (explizit)

- Kein provider-spezifisches End-to-End-Implementierungsdetail auf API-Ebene
  (Adapter bleibt separates Thema).
- Keine sofortige produktive Migration bestehender Tenants in diesem Work-Package.
- Kein Breaking-Change am bestehenden `/analyze`-Contract.

### Offene Risiken (v1)

1. **Out-of-order-Intensität höher als erwartet**
   - Risiko: inkonsistente Lifecycle-Stände
   - Mitigation: strengere Versionierung + Quarantäne-Queue
2. **Metering-Drift bei Partial-Failures**
   - Risiko: falsche Abrechnung oder Overblocking
   - Mitigation: Reconcile-Job + Audit-Delta-Report
3. **Suspend/Compliance-Overrides kollidieren mit Billing-Recovery**
   - Risiko: unklare Priorität in Randfällen
   - Mitigation: explizite Prioritätsregel `suspended` > `active/grace`

## DoD-Abdeckung (#586)

- Zustandsmodell + Übergangsregeln: Abschnitt 2
- Idempotenz- und Fehlerbehandlungsstrategie: Abschnitt 3
- Metering-Granularität + Aggregationslogik: Abschnitt 4
- Non-Goals / offene Risiken: Abschnitt 5

## Nächster Schritt

Oldest-first im Parent #577: #587 (Async-Analyze Domain-Design) umsetzen.
