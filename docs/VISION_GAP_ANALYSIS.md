# Vision ↔ Ist-Stand: Differenz-Protokoll

> Stand: 2026-09-21 · Basiert auf `docs/VISION_PRODUCT.md`, `docs/ROADMAP_TO_VISION_V1.md`, `docs/GO_TO_MARKET_MVP.md`
> Zweck: Strukturierte Gegenüberstellung der Produktintention mit dem tatsächlichen Umsetzungsstand, inkl. dokumentierter Differenzen und Maßnahme zur Schließung.

---

## 1) Die Intention in Kürze

Ein **Geo Intelligence Portal Schweiz**: Nutzer geben eine Adresse ein oder klicken auf die Karte und erhalten belastbare Standort- und Gebäudeinformationen. Zwei unabhängig vermarktbare Surfaces:

- **API (B2B)**: maschinenlesbar, versioniert, Explainability, Tiered Access per Plan/Entitlement
- **GUI (Endnutzer)**: Adresseingabe + Kartenklick + Ergebnis-Panel

Kernmodule M1–M5 (Gebäudeprofil, Umfeldprofil, Bau-Eignung, Explainability, API+GUI), umgesetzt als API-first Verticals mit Incremental Shipping.

---

## 2) Umsetzungs-Stand (Inventur 2026-09-21)

| Modul | Intention | Ist-Stand | Deckung |
|---|---|---|---|
| **M1 Gebäudeprofil** | Adress-Geocoding, Gebäudetyp/Baujahr/Energie | `src/api/address_intel*.py`, GWR-Decode, Source-Registry mit Confidence | ✅ ~90% |
| **M2 Umfeldprofil** | ÖV, POI, Lärm, Scoring | Adaptive Radius-Fallbacks, `environment_profile` mit 6-Faktor-Scoring, POI-Referenzpunkte | ✅ ~85% |
| **M3 Bau-Eignung** | Kartenklick → Standortanalyse | `suitability_light`, Koordinaten-Input | ✅ ~80% |
| **M4 Explainability** | Quelle/Aktualität/Vertrauen je Feld | Provenance, `derived_from`, Confidence, `score_model` | ✅ ~85% |
| **M5 API+GUI** | API-first, 2 Surfaces | API-Contract v1, GUI-MVP mit OSM-Karte, 2-Container-Deploy auf dev | ✅ ~75% |

Technisch: Async-Runtime (Jobs, Worker, Result-Pages, Notifications), OIDC/BFF-Auth, Structured Logging, CI/CD mit 6 grünen Checks — laut Roadmap ~80% der technischen Basis.

---

## 3) Differenzen (Gap-Liste)

### G1 — Staging/Prod-Umgebungen ✅ gestrichen (Entscheid 2026-09-21)
- **Ursprüngliche Intention:** Promotion-Pfad `dev → staging → prod`, produktives TLS, Custom Domain, Monitoring+Alerting auf Prod
- **Neue Entscheidung:** Staging/Prod werden **nicht** aufgebaut — solange das initiale Produkt in dev nicht existiert, braucht es keine andere Umgebung. Dev ist die Produktbasis.
- **Ist-Befund (historisch):** Staging-Terraform (`staging_*.tf`) und `deploy-staging.yml` existierten, wurden aber nie ausgeführt; keine `prod`-Terraform-Dateien. Die bestehenden Staging-Artefakte werden nicht weiterverfolgt; Wiedereinführung ist ein bewusster Folgeentscheid.
- **Maßnahme:** Keine — Gap durch Entscheidung aufgelöst. Phase 1 der Roadmap heißt jetzt „Initiales Produkt auf dev".

### G2 — Entitlement-Datenschicht unvollständig 🔴 (Phase 2, kritischer Pfad)
- **Intention:** Tabellen `organizations, users, memberships, plans, subscriptions, entitlements, usage_counters, api_keys, audit_events` (GTM_TO_DB_ARCHITECTURE_V1.md)
- **Ist:** `001_core_schema.sql` liefert nur `organizations/users/memberships/api_keys`. **`plans/subscriptions/entitlements/usage_counters/audit_events` fehlten komplett** — Migration `004_entitlements_schema.sql` (dieses PR) schließt die Schema-Lücke. Runtime-Gates (Deep-Mode-`allowed`/`quota_remaining`) sind vertragsgemäß implementiert, lesen aber Client-Inputs statt DB-Entitlements
- **Maßnahme:** ✅ Schema-Migration ergänzt; offen: Runtime-Bindung an `entitlements`-Tabelle + `usage_counters`-Metering

### G3 — Quota-Enforcement ohne persistente Zähler 🟡 (Phase 2 — Runtime gebunden)
- **Intention:** „API-Request mit überschrittener Quota liefert deterministisch 429“ (Roadmap Exit-Kriterium)
- **Ist:** Runtime-Bindung ergänzt: `src/shared/quota_ledger_db.py` (`DbQuotaLedger`) reserviert Deep-Mode-Einheiten atomar in `usage_counters` (Migration 004) und liest Limits aus `entitlements`; `QUOTA_STORE_BACKEND=db` aktiviert den serverseitigen Pfad (Default `none` = legacy Client-Quota, fail-safe). `_apply_deep_mode_runtime_status` ersetzt die clientgelieferte `quota_remaining` serverseitig und degradiert bei Ledger-Erschöpfung deterministisch auf `fallback_reason=quota_exhausted` (kein 429 — der Deep-Mode-Contract verbietet die Blockade des Basisergebnisses; 429 bleibt hartem Rate-Limiting vorbehalten, `docs/api/contract-v1.md`). Bei Ledger-Fehlern wird fail-safe auf die Client-Quota zurückgefallen (strukturierte Warnung `api.entitlements.quota_ledger_error`).
- **Maßnahme:** ✅ Runtime gebunden; offen: Org-Bootstrap (UUID-Org-Rows statt `default-org`-Strings) und Verankerung der Downgrade- vs. 429-Semantik pro Endpoint im Contract

### G4 — Billing/Stripe nicht integriert 🔴 (Phase 2)
- **Intention:** Stripe-Webhook → Subscription-Lifecycle, idempotent
- **Ist:** Nur Contracts/Design (`entitlement-billing-lifecycle-v1.md`, `bl30-entitlement-contract-v1.md`); kein Stripe-SDK, kein Webhook-Endpoint
- **Maßnahme:** Offen — Sequenziell nach G3 (GTM-Gate erfüllt via GTM-DEC-002)

### G5 — GTM-Validierung ✅ (gestrichen als Gap)
- **Intention:** 10 Discovery-Gespräche, Go/Adjust/Stop-Entscheidung vor Entitlement-Implementierung
- **Ist:** Sprint `gtm-validation-001` durchgeführt; Entscheidung GTM-DEC-002 dokumentiert und akzeptiert (Option 2: BL-30.2 nach BL-30.1 priorisiert); `reports/testing/gtm-validation/gtm-validation-001/summary.md` als Evidenz abgelegt. Entitlement-Implementierung ist damit entblockt — die Roadmap (Stand 2026-03-01) hatte den Sprint fälschlich noch als ausstehend geführt; entsprechend korrigiert.
- **Maßnahme:** Keine weiteren Kundengespräche vorgesehen

### G6 — POI-Abdeckungs-Baseline unter Ziel 🟡 (Phase 3)
- **Intention:** „POI-Abdeckung für Top-20-Adressen ohne `low_confidence`-Fallback"; Abdeckungsmonitoring; Roadmap: „Baseline-Messung auf 20 Referenz-Adressen"
- **Ist:** Nur **5** Referenzpunkte in `tests/data/poi_reference_points_v1.json` (ZH HB, St. Gallen, Bern, Lugano, Appenzell + remote) — Ziel waren 20; kein periodisches Abdeckungsmonitoring
- **Maßnahme:** Offen — Referenzpunkte auf 20 erweitern (Covering alle CH-Sprachregionen)

### G7 — Deep Mode ohne echte Tiefenquellen 🟡 (Phase 3)
- **Intention:** Mind. 1 echte Tiefenquelle (z. B. kantonale Planungsdaten) mit `confidence >= 0.7`
- **Ist:** Deep-Mode-Orchestrierung + Open-Meteo-Enrichment-Prototyp (`open_meteo_forecast`); keine registerbasierten Tiefenquellen (Bebauungspläne, Kataster)
- **Maßnahme:** Offen — Externe Datenlizenz nötig (Owner-Entscheidung); Open-Meteo ist bewusster Open-Data-Einstieg

### G8 — Self-Service-Checkout / HTML5-UI / Mobile 🟡 (Phase 4)
- **Intention:** Self-Service Signup→Payment→API-Key, Lighthouse-Budgets, Mobile Geolocation
- **Ist:** Spezifiziert (`HTML5_UI_ARCHITECTURE_V1.md`, `mobile-live-geolocation-contract-v1.md`), teils umgesetzt (GUI-Performance-Tests, Mobile-Smokes existieren); kein Checkout
- **Maßnahme:** Offen — Sequenziell nach Phase 1+2

---

## 4) Wie wurde umgesetzt (Bewertung des Wegs)

**Stärken (Intention ↔ Umsetzung konsistent):**
- API-first ist real gelebt: Jede GUI-Funktion geht über API-Endpunkte; Contract-Tests sichern Stabilität (`contract-tests.yml`, `test_api_contract_v1.py`)
- Explainability (M4) ist tief umgesetzt: `source_catalog`, `derived_from`-Projektion, `score_model` mit Formel + Gewichten je Faktor — übertrifft MVP-Anspruch
- Deep-Mode-Gate folgt exakt der dokumentierten Fallback-Matrix, inkl. Telemetrie-Events (`api.deep_mode.gate_evaluated` … `execution.end`)
- Governance-Infrastruktur (Boundary-Checks, Doc-Drift-Tests, Deploy-Gates) ist außergewöhnlich diszipliniert

**Schwächen (Abweichungen von der Intention):**
- **Doku-Code-Drift bei Infrastruktur (aufgelöst):** Staging-Terraform + Workflow existierten, wurden aber nie ausgeführt — Docs versprachen einen Promotion-Pfad, den es real nicht gab; mit Entscheid 2026-09-21 (Staging/Prod gestrichen) ist dieser Drift aufgelöst (G1)
- **Entitlement-Gates sind Schattenlogik:** Die Gate-Auswertung ist technisch sauber, operiert aber auf vom Client gelieferten `options.entitlements.*`-Feldern statt auf serverseitigem Tenant-Zustand — für B2B-Vermarktung nicht belastbar (G2/G3)
- **Vision-Doku verspricht `plans/subscriptions/...`-Tabellen**, das DB-Schema stoppte bei `api_keys` (G2 — in diesem PR geschlossen)

---

## 5) Maßnahme dieses PR

| Gap | Aktion | Status |
|---|---|---|
| G2 (Schema) | `db/migrations/004_entitlements_schema.sql`: `plans`, `subscriptions` (inkl. 1-aktiv-pro-Org-Partial-Index), `entitlements` (normalisiert, historisierbar), `usage_counters` (Scope-Modell org/user/api_key + Fenster), `audit_events` (append-only) | ✅ neu |
| G3 | Server-seitiges Quota-Ledger (`DbQuotaLedger` über `usage_counters`/`entitlements`, `QUOTA_STORE_BACKEND=db`), fail-safe Fallback auf Client-Quota | ✅ neu |
| G6 (Protokoll) | Differenz-Protokoll als lebendes Dokument etabliert | ✅ neu |
| G5 | GTM-Gate als erfüllt dokumentiert (GTM-DEC-002); Roadmap-/Gate-Doku korrigiert | ✅ neu |
| G1 | Staging/Prod gestrichen — Dev ist Produktbasis (Entscheid 2026-09-21) | ✅ neu |
| G3, G4, G7, G8 | Bleiben offen, Ownership + Reihenfolge dokumentiert | 📋 diesem Dokument |

**Nächste Schritte (empfohlene Reihenfolge):**
1. Initiales Produkt auf dev vervollständigen und abnehmen (Async UX, M1–M5-Abnahme) — ehem. G1
2. Entitlement-Runtime-Bindung Entitlements/Usage-Counters (G3) — ✅ erledigt; offen: Org-Bootstrap (UUID-Org-Rows)
3. POI-Referenzpunkte 5→20 erweitern + Monitoring etablieren (G6)
4. Billing-Integration Stripe (G4) — nach G3

---

*Lebendes Dokument: Bei Änderung an Vision, Roadmap oder Umsetzungsstand zu aktualisieren.*
