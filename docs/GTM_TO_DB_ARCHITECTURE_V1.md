# GTM → Data Architecture Mapping v1

Stand: 2026-03-01  
Issue: #585 (Parent #577)

## Ziel des Work-Packages

Dieses Dokument übersetzt die bereits vorliegenden GTM-Entscheidungen in ein
kanonisches, multi-tenant-fähiges Datenmodell für geo-ranking.

**Scope dieses Work-Packages (#585):**
- GTM-Entscheidungsmatrix (Business-Entscheid → technische Konsequenz)
- Kanonisches Kern-Datenmodell v1
- Tenant-Grenzen und Ownership-Regeln
- Transparente Trade-offs / offene Fragen

**Nicht Teil dieses Work-Packages:**
- Detailliertes Billing-State-Machine-Design (Folge: #586)
- Async-Analyze Domain-Design inkl. Job-States/Result-Pages (Folge: #587)
- MVP→Scale Migrations-/Rollout-Plan (Folge: #588)

## Inputs (GTM-/Contract-Basis)

- [`docs/GO_TO_MARKET_MVP.md`](GO_TO_MARKET_MVP.md)
- [`docs/PRICING_TIER_LIMIT_MATRIX_V1.md`](PRICING_TIER_LIMIT_MATRIX_V1.md)
- [`docs/api/bl30-entitlement-contract-v1.md`](api/bl30-entitlement-contract-v1.md)
- [`docs/api/bl30-checkout-lifecycle-contract-v1.md`](api/bl30-checkout-lifecycle-contract-v1.md)
- [`docs/BL30_REBUILD_VS_AUSBAU_GUARDRAILS_API_FIRST_V1.md`](BL30_REBUILD_VS_AUSBAU_GUARDRAILS_API_FIRST_V1.md)

## GTM → technische Konsequenzen (v1)

| GTM-Entscheid | Technische Konsequenz (Datenmodell) | Begründung |
| --- | --- | --- |
| B2B-Fokus mit Team-/Org-Kontext | `organizations` als Primär-Tenant; `memberships` für User↔Org-Rollen | Vermeidet user-zentrierte Dateninseln und erlaubt sauberes Org-Offboarding |
| Tiered Pricing (Free/Pro/Business) | Versioniertes `plans`-Objekt + `subscriptions` pro Org | Planwechsel ohne historische Datenverluste; Auditierbarkeit |
| Capability-/Entitlement-Gates sind produktentscheidend | Eigene `entitlements`-Tabelle (normierte Keys) statt nur JSON-Blob | Deterministische Auswertung im Runtime-Pfad |
| API-first + additive Evolution | Stabile IDs/Ownership-Schlüssel (`org_id`, `subscription_id`, `user_id`) | Schützt bestehende Contracts und ermöglicht iterative Erweiterung |
| Nutzungsbasierte Limits (monatlich + burst) | `usage_counters` auf Scope `org|user|api_key` + Zeitfenster | Einheitliche Metering-Basis für Billing und Runtime-Gates |
| API-Key-Zugriff pro Tenant | `api_keys` gehören zu einer Org, optional mit user-bezogenem Issuer | Least-Privilege + revocable Zugriffspfade |
| Nachvollziehbarkeit/Audit als Pflicht | Unveränderliches `audit_events`-Log mit Actor/Scope/Action | Security/Compliance + Debug-Fähigkeit ohne implizite Seiteneffekte |
| Provider-Lock vermeiden (Stripe etc.) | `billing_provider` + `provider_reference` abstrahieren Event-Quelle | Erlaubt Providerwechsel bei konstantem Domänenmodell |

## Kanonisches Kern-Datenmodell v1

### Entity-Katalog (MVP+)

1. **organizations**
   - Zweck: kanonischer Tenant
   - Schlüssel: `id`, `external_ref?`, `status`, `created_at`

2. **users**
   - Zweck: Identitäten (menschlich/technisch)
   - Schlüssel: `id`, `email_hash`, `status`

3. **memberships**
   - Zweck: User-Rolle innerhalb einer Org
   - Schlüssel: `id`, `org_id`, `user_id`, `role`, `status`, `created_at`

4. **plans**
   - Zweck: pricing-/packaging-definierte Planversionen
   - Schlüssel: `id`, `plan_code`, `version`, `active_from`, `active_to?`

5. **subscriptions**
   - Zweck: zugewiesener Plan pro Org + Lifecycle-Metadaten
   - Schlüssel: `id`, `org_id`, `plan_id`, `state`, `billing_provider`, `provider_ref`

6. **entitlements**
   - Zweck: effektive Capability-/Limit-Werte je Org (abgeleitet aus Plan + Overrides)
   - Schlüssel: `id`, `org_id`, `subscription_id`, `key`, `value`, `source`, `effective_from`

7. **usage_counters**
   - Zweck: Metering für Limits/Abrechnung
   - Schlüssel: `id`, `org_id`, `scope_type`, `scope_id`, `metric_key`, `window_start`, `window_end`, `value`

8. **api_keys**
   - Zweck: API-Zugriff auf Tenant-Ressourcen
   - Schlüssel: `id`, `org_id`, `issued_by_user_id?`, `fingerprint`, `status`, `rotated_at?`

9. **audit_events**
   - Zweck: unveränderliche Nachvollziehbarkeit sicherheits-/billingrelevanter Aktionen
   - Schlüssel: `id`, `org_id`, `actor_type`, `actor_id`, `action`, `entity_type`, `entity_id`, `occurred_at`

### Beziehungsskizze (logisch)

- `organizations 1:n memberships`
- `users 1:n memberships`
- `organizations 1:n subscriptions`
- `plans 1:n subscriptions`
- `subscriptions 1:n entitlements`
- `organizations 1:n api_keys`
- `organizations 1:n usage_counters`
- `organizations 1:n audit_events`

## Tenant-Grenzen & Ownership-Regeln (verbindlich v1)

1. **Org ist harte Datengrenze.**
   Alle produktiven Records tragen `org_id` (direkt oder transitiv referenzierbar).

2. **User ohne Membership hat keinen Tenant-Zugriff.**
   Auth reicht nicht; nur Membership autorisiert Datenzugriff.

3. **Subscription ist eindeutig pro Org aktiv.**
   Parallelhistorie erlaubt, aber genau eine aktive Subscription je Org.

4. **Entitlements sind tenant-lokal evaluierbar.**
   Runtime darf keine globalen Side-Channels für Gate-Entscheide benötigen.

5. **API-Keys sind tenant-gebunden und rotierbar.**
   Keine org-übergreifende Wiederverwendung von Key-Fingerprints.

6. **Audit-Events sind append-only.**
   Korrekturen über kompensierende Events, nicht durch Mutation historischer Einträge.

## No-regrets Defaults (für Umsetzung)

- UUID/ULID-basierte IDs für alle Kernobjekte (keine semantischen Primärschlüssel)
- UTC-Timestamps in allen Lifecycle-/Audit-Tabellen
- Soft-Delete nur dort, wo fachlich nötig; ansonsten Statusfelder + Audit-Trail
- Explizite Zustandsfelder (`status`/`state`) statt impliziter Bool-Kombinationen
- Additive Schema-Evolution als Default (Guardrail: keine Breaking-Contracts)

## Trade-offs / offene Fragen

1. **`entitlements` als normalisierte Tabelle vs. JSON-Dokument**
   - Entscheidung v1: normalisiert (bessere Prüfbarkeit)
   - Trade-off: mehr Schema-/Migrationsaufwand bei neuen Keys

2. **Metering-Granularität (`org` nur vs. `org+user+api_key`)**
   - Entscheidung v1: generisches Scope-Modell (`scope_type`, `scope_id`)
   - Trade-off: höhere Aggregationskomplexität

3. **Plan-Versionierung (harte Versionen vs. mutable Plan-Objekte)**
   - Entscheidung v1: versioniert und historisierbar
   - Trade-off: mehr Verwaltungslogik bei Rollout/Backfill

4. **Provider-Abstraktionstiefe für Billing**
   - Entscheidung v1: minimale Abstraktion (`provider`, `provider_ref`, idempotente Event-ID)
   - Trade-off: provider-spezifische Sonderfälle bleiben in Adapter-Schicht

## Übergabe an Folge-Work-Packages

- **#586** konkretisiert Entitlement-/Billing-Lifecycle inkl. idempotenter Eventverarbeitung.
- **#587** definiert das Async-Analyze-Domänenmodell (`jobs`, `job_events`, `job_results`, Notifications).
- **#588** liefert den MVP→Scale-Rollout inkl. atomisierbarer Umsetzungs-Issues.
