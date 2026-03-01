# Roadmap to Vision — Geo Intelligence Portal Schweiz

Stand: 2026-03-01  
Kontext: Ehrliche Standortbestimmung und Pfad vom heutigen Stand zum vollständigen Produktzielbild.

---

## 1 Zielbild-Recap

Das Ziel ist ein **Geo Intelligence Portal für die Schweiz**: Nutzer geben eine Adresse ein oder klicken einen Punkt auf der Karte, und erhalten sofort belastbare Standort- und Gebäudedaten — aus vertrauenswürdigen Quellen (swisstopo, GWR, OSM), nachvollziehbar und reproduzierbar.

Das Produkt besteht aus zwei unabhängig vermarktbaren Surfaces:

- **API (B2B/Integration):** maschinenlesbarer Webservice, stabile Versionierung, Explainability-Felder, Tiered Access per Plan/Entitlement
- **GUI (Endnutzer/Demos):** Adresseingabe + Kartenklick, Ergebnisdarstellung, Async-Jobs für Deep-Mode-Anfragen

Kernmodule (M1–M5): Gebäudeprofil, Umfeldprofil, Bau-Eignung, Explainability, API+GUI — alle konzipiert und als erste Version deploybar.

---

## 2 Aktueller Stand

| Dimension | Reifegrad | Kurzbeschreibung |
|---|---|---|
| **Technisch** | ~80 % | API mit M1–M5, Async Runtime, 2-Container-Deployment auf dev, CI/CD, OIDC, Logging/Tracing — stabil und deploybar. Hauptlücke: kein Prod-Environment. BL-15 abgeschlossen (Architekturentscheid 2026-03-01). |
| **Produktreife** | ~50 % | Sync-Analyze produktiv nutzbar, Async UX spezifiziert aber nicht deployed, kein Entitlement-Layer, Intelligence-Qualität in Teilen noch schwach (POI-Dichte, Deep Mode ohne echte Tiefenquellen). |
| **Kommerziell** | ~25 % | GTM-Architektur und Pricing-Hypothesen vollständig dokumentiert (BL-30, `docs/GTM_TO_DB_ARCHITECTURE_V1.md`, `docs/api/entitlement-billing-lifecycle-v1.md`). Kein Billing, keine Subscriptions, keine zahlenden Kunden. GTM-Validierungssprint (#457) noch ausstehend. |

### Was bereits fertig ist

- M1–M5 (Gebäudeprofil, Umfeldprofil, Bau-Eignung am Punkt, Explainability, API+GUI) ✅
- API-Contract v1, Field-Catalog, Scoring-Methodology, Preference-Profiles, Personalization ✅
- Async Runtime Skeleton + Worker Pipeline + Result-Delivery + Notifications (in-app) ✅
- GTM-Architektur, Pricing-Tiers, Entitlement-Contract, Checkout-Lifecycle-Design ✅
- Async Domain Design, Result-Pages, Retention-Cleanup (alle spezifiziert und implementiert, dev-only) ✅
- 2-Container-Deploy (API + UI), OIDC, Structured Logging, Trace-Debug-View, CI/CD ✅

### Was noch fehlt (strukturiert)

1. **Prod-Environment** → Alles läuft auf `dev`; Staging/Prod noch nicht provisioniert
3. **Async UX live** → Jobs, Progress, Notifications, Result-Pages sind implementiert, aber nicht in Prod deployed
4. **Entitlement-Layer (G3)** → Org/User/Plan/Subscription/Quota noch nicht implementiert; beginnt nach #457-Close
5. **Billing/Checkout** → kein Stripe oder Äquivalent; kein Self-Service-Zugang
6. **Intelligence-Qualität** → POI-Dichte partiell schwach; Deep Mode ohne echte Tiefenquellen (Bebauungspläne, Kataster etc.)

---

## Phase 1 — Production Gate

**Ziel:** Produktiv-Umgebung bereitstellen, Legacy-IAM-Blocker auflösen, Async UX live bringen.

### Deliverables

- **BL-15 Resolution:** ✅ Abgeschlossen (Architekturentscheid 2026-03-01). Externer Consumer (`76.13.144.185`) bleibt dauerhaft aktiv — bewusste Architekturentscheidung, kein Blocker für Prod-Gate. Referenz: `docs/LEGACY_IAM_USER_READINESS.md`, `docs/LEGACY_CONSUMER_INVENTORY.md`.
- **Staging/Prod provisionieren:** IaC-Erweiterung (Terraform) für `staging`- und `prod`-Umgebung; Promotion-Pfad `dev → staging → prod` aktivieren. Referenz: `docs/ENV_PROMOTION_STRATEGY.md`.
- **Async UX deployen:** Jobs-API, Result-Pages, In-App-Notifications und Result-Permalinks auf Prod ausrollen; Monitoring-Runbook aktivieren. Referenz: `docs/api/async-analyze-domain-design-v1.md`, `docs/api/async-delivery-ops-runbook-v1.md`.
- **TLS + Custom Domain Prod:** Produktives Zertifikat, Route53-Eintrag, CORS-Policy für Prod-Origins. Referenz: `docs/TLS_CERTIFICATE_MIGRATION_RUNBOOK.md`.

### Exit-Kriterien

| Kriterium | Nachweis |
|---|---|
| BL-15: ✅ Abgeschlossen (Architekturentscheid 2026-03-01, kein Blocking) | Externer Consumer bleibt dauerhaft aktiv — accepted. Referenz: `docs/LEGACY_IAM_USER_READINESS.md` |
| Prod-Deployment läuft stabil (`services-stable`) | GitHub Actions Run + Post-Deploy-Verify via `check_deploy_version_trace.py` |
| `POST /analyze` auf Prod: HTTP 200, korrekte Response-Struktur | Internet-Smoke `run_remote_api_smoketest.sh` gegen Prod-URL |
| Async-Job Lifecycle `queued → completed` auf Prod nachweisbar | E2E-Test gegen Prod-Job-Endpoints |
| Monitoring + Alerting aktiv (Telegram-Alert bei Ausfall) | CloudWatch-Alarm verifiziert |

**Abhängigkeiten:** Prod-AWS-Account-Konfiguration  
**Komplexität:** Mittel (BL-15 abgeschlossen; dominanter Faktor: Prod-IaC-Provisionierung)

---

## Phase 2 — Entitlement & Erster Zahlender Kunde

**Ziel:** Plan-basierter API-Zugang live; erster Kunde zahlt für Zugang.

### Deliverables

- **GTM-Validierungssprint (#457):** 10 strukturierte Kunden-Discovery-Gespräche (Segmente A/B/C), Entscheidung Go/Adjust/Stop nach `docs/PACKAGING_PRICING_HYPOTHESES.md`. Ohne diesen Sprint kein Entitlement-Implementierungs-Go.
- **Entitlement-Layer implementieren:** Tabellen `organizations`, `users`, `memberships`, `plans`, `subscriptions`, `entitlements`, `usage_counters`, `api_keys`, `audit_events`. Architektur: `docs/GTM_TO_DB_ARCHITECTURE_V1.md`, Contract: `docs/api/entitlement-billing-lifecycle-v1.md`, `docs/api/bl30-entitlement-contract-v1.md`.
- **API-Key-Provisioning:** Org-basierte API-Keys, Rotation, Revocation.
- **Rate-Limiting / Quota-Enforcement:** Gateway oder Middleware-seitiges Entitlement-Gate (monatliches Limit + Burst-Rate).
- **Billing-Integration (Minimal):** Stripe-Webhook → Subscription-Lifecycle (`created|upgraded|downgraded|canceled`); idempotente Verarbeitung. Referenz: `docs/api/bl30-checkout-lifecycle-contract-v1.md`.
- **Manuelles Onboarding (Pilot):** Erster zahlender Pilot-Kunde (Segment A oder C) per manuellem Onboarding und Rechnungsstellung.

### Exit-Kriterien

| Kriterium | Nachweis |
|---|---|
| GTM-Sprint abgeschlossen, Entscheidung dokumentiert | `docs/testing/GTM_VALIDATION_DECISION_LOG.md` mit Go/Adjust/Stop |
| Plan-Matrix live: Free/Pro/Business mit unterschiedlichen Quotas | API-Request mit überschrittener Quota liefert deterministisch 429 |
| API-Key-Flow End-to-End: Provisioning → Nutzung → Rotation | Manuelle E2E-Durchführung + Smoke-Test |
| Erster zahlender Kunde aktiv | Stripe-Subscription aktiv, API-Key ausgestellt, mindestens 1 bezahlte Analyse |
| Subscription-Lifecycle (Upgrade/Downgrade/Cancel) ohne manuelle DB-Eingriffe | Webhook-Idempotenz-Test mit wiederholtem Event |

**Abhängigkeiten:** Phase 1 abgeschlossen (Prod live), #457-Close (GTM-Entscheidung), Datenbankwahl final (PostgreSQL/DynamoDB per `docs/GTM_TO_DB_ARCHITECTURE_V1.md`)  
**Komplexität:** Hoch (Implementierung + GTM-Koordination)

---

## Phase 3 — Async UX & Intelligence-Qualität (parallel laufende Schiene)

**Ziel:** Produkterlebnis verbessern; Deep Mode mit echten Tiefenquellen; POI-Dichte stabilisieren. Diese Phase läuft **parallel** zu Phase 2 und ist keine Blockierung.

### Deliverables

- **Async UX produktiv:** Result-Pages als eigenständige Seiten (Deep-Link auf `result_id`); Job-Progress-Anzeige in GUI; Notifications (in-app, optional E-Mail) für lange Läufe. Referenz: `docs/api/async-analyze-domain-design-v1.md`.
- **POI-Quellen verdichten:** Zusätzliche OSM-Kategorien auswerten; Fallback-Strategie bei dünner Datenlage dokumentieren und implementieren; Abdeckungsmonitoring einführen.
- **Deep Mode mit echten Tiefenquellen:** Mindestens eine echte Tiefenquelle integrieren (z. B. Gebäudeenergieverbrauchsdaten, kantonale Planungsdaten); Contract-Felder und Explainability-Feld `derived_from` füllen. Referenz: `docs/api/deep-mode-contract-v1.md`, `docs/api/deep-mode-orchestration-guardrails-v1.md`.
- **Scoring-Kalibrierung:** Golden-Testset erweitern; Scoring-Methodologie iterieren basierend auf Pilot-Kunden-Feedback.

### Exit-Kriterien

| Kriterium | Nachweis |
|---|---|
| Async-Job via GUI vollständig bedienbar (submit → progress → result-page) | GUI-E2E-Smoke mit manuellem Nachweis |
| POI-Abdeckung für Top-20-Adressen ohne `low_confidence`-Fallback | Smoke-Test auf Referenz-Adressen |
| Deep Mode liefert mind. 1 echte externe Quelle mit `confidence >= 0.7` | Contract-konformes Response mit befülltem `derived_from` |
| Scoring-Golden-Tests: kein Drift gegenüber dokumentierter Methodologie | `pytest tests/test_scoring_methodology_golden.py` → grün |

**Abhängigkeiten:** Phase 1 (Prod-Env für echte Daten), ggf. externe Datenlizenz-Verhandlungen  
**Komplexität:** Mittel (iterativ; keine harte Sequenzabhängigkeit)

---

## Phase 4 — Self-Service & Scale

**Ziel:** Vollständig selbst-bedienbares Produkt; HTML5-UI produktiv; skalierungsfähiger Multi-Tenant-Betrieb.

### Deliverables

- **Self-Service Checkout:** öffentliches Pricing-/Signup-Flow; Kreditkartenzahlung über Stripe-Checkout; automatisches API-Key-Provisioning ohne manuelle Intervention.
- **Subscription-Dashboard:** Org-Übersicht, Nutzungsanzeige, Plan-Upgrade/-Downgrade self-service, Rechnungshistorie.
- **HTML5 UI (BL-30.4):** Vollständige Client-Side-Architektur mit Performance-Budget, Explainability-UX, Mobile-Support. Referenz: `docs/gui/HTML5_UI_ARCHITECTURE_V1.md`, `docs/gui/HTML5_UI_PERFORMANCE_BUDGET_CACHING_V1.md`.
- **Karten-Experience (BL-30.5):** OSM-Tile-Integration produktiv (eigenes Tile-Serving, ODbL-konform), Bau-/Zufahrtseignungsanzeige auf der Karte. Referenz: `docs/gui/OSM_TILE_ODBL_COMPLIANCE_DECISION_V1.md`.
- **Mobile Live-Geolocation (BL-30.6):** Permission-Flow, Koordinaten-Analyse, Privacy-Guardrails. Referenz: `docs/api/mobile-live-geolocation-contract-v1.md`.
- **Skalierungs-Infrastruktur:** Auto-Scaling ECS, DB-Connection-Pooling, Multi-AZ-Vorbereitung, SLA-Definition.

### Exit-Kriterien

| Kriterium | Nachweis |
|---|---|
| Self-Service-Signup ohne manuellen Eingriff End-to-End lauffähig | Smoke: Signup → Payment → API-Key in < 5 Minuten |
| Mind. 10 zahlende Kunden, > 0 Churn in 30 Tagen | CRM/Stripe-Auswertung |
| HTML5 GUI: LCP < 2.5s, kein Layout-Shift auf Core-Flows | Lighthouse-Messung auf Prod |
| Mobile Geolocation: Permission → Analyse in < 30s | Manuelle E2E auf iOS/Android |
| Service-Verfügbarkeit Prod: > 99.5 % in 30 Tagen | CloudWatch-Alarm-Auswertung |

**Abhängigkeiten:** Phasen 1+2 abgeschlossen, OSM-Tile-Hosting-Entscheid umgesetzt, Legal-Review Datenschutz (Mobile)  
**Komplexität:** Hoch (breit; mehrere unabhängige Streams parallelisierbar)

---

## 5 Kritischer Pfad

```
BL-15 ✅ Abgeschlossen (Architekturentscheid 2026-03-01)

Prod-Deployment (Phase 1) ──────────────────────────────────────────┐
    │                                                                 │
    ▼                                                                 │
GTM-Sprint #457 abschließen                                          │ Phase 3
    │                                                                 │ (parallel)
    ▼                                                                 │
Entitlement-Layer implementieren (Phase 2)                           │
    │                                                                 │
    ▼                                                                 │
Erster zahlender Kunde ◄─────────────────────────────────────────────┘
    │
    ▼
Self-Service-Checkout + HTML5 UI + Mobile (Phase 4)
```

**Zwingend sequenziell:**
1. ~~BL-15 muss vor Prod-Deploy geschlossen sein~~ → ✅ abgeschlossen (Architekturentscheid 2026-03-01, kein Blocker mehr)
2. GTM-Sprint (#457) muss vor Entitlement-Implementierung abgeschlossen sein (kein Code ohne validiertes Pricing)
3. Entitlement-Layer muss vor Self-Service-Checkout existieren

**Parallelisierbar:**
- Intelligence-Qualität (POI, Deep Mode) läuft parallel zu Phase 2
- Async UX Verbesserungen können nach Phase 1 unabhängig vom Entitlement-Track deployed werden
- HTML5 UI-Architektur kann vorbereitet werden, sobald Prod stabil läuft

---

## 6 Offene Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|---|---|---|---|
| ~~**BL-15 extern**~~: Consumer `76.13.144.185` — **Architekturentscheid 2026-03-01: bleibt dauerhaft aktiv, accepted** | — | — | BL-15 abgeschlossen; kein Prod-Gate-Blocker mehr |
| **GTM-Sprint**: Pilot-Gespräche zeigen klares Stop-Signal (kein Markt-Fit) | Niedrig–Mittel | Hoch — Pivoting nötig; Entitlement-Scope unklar | Stop-Kriterium explizit in Decision-Log; Pivot-Optionen (anderes Segment, API-only) vorformulieren |
| **Datenlizenz**: Tiefenquellen (kantonale Daten) nicht lizenzierbar oder prohibitiv teuer | Mittel | Mittel — Deep Mode bleibt schwach | Frühzeitig Lizenzanfragen stellen; Fallback auf ausschließlich offene Daten dokumentieren |
| **Entitlement-Komplexität**: Multi-Tenant-Datenschicht dauert länger als geplant | Mittel | Mittel — Verzögerung Phase 2 | Scope-Minimalversion (nur Free/Pro, kein Business-Tier initial) als Fallback |
| **OSM-Tile-Hosting**: Eigener Tile-Server ist Infra-Aufwand; Drittanbieter hat Lizenzbedingungen | Mittel | Mittel — Karten-Feature verzögert | Entscheid gemäß `docs/gui/OSM_TILE_ODBL_COMPLIANCE_DECISION_V1.md`; Drittanbieter-Fallback evaluieren |
| **Scaling**: Unerwartet hoher Traffic führt zu DB-Engpässen (usage_counters, jobs) | Niedrig | Hoch | Connection-Pooling und horizontales Scaling von Anfang an einplanen; Load-Test in Staging vor Prod |

---

## 7 Erfolgsmessung

### Phase 1 — abgeschlossen, wenn:
- Prod-URL öffentlich erreichbar, HTTPS mit gültigem Zertifikat
- `/health` liefert 200, `/analyze` liefert korrekte Intelligence-Response
- BL-15 ✅ Abgeschlossen (Architekturentscheid 2026-03-01)

### Phase 2 — abgeschlossen, wenn:
- **Erster zahlender Kunde** mit aktivem API-Key, bezahlter Subscription, nachgewiesener Analyse-Nutzung
- Quota-Enforcement funktioniert (Overshoot → 429, kein Silent-Overflow)
- Onboarding-Zeit (Signup bis erster erfolgreicher Request) < 1 Stunde

### Phase 3 — laufend messbar:
- POI-Abdeckung: < 5 % der Analysen liefern `environment_profile.score.overall = null`
- Deep Mode: mind. 1 Tiefenquelle aktiv, `confidence >= 0.7` auf definierten Test-Adressen
- Kundenzufriedenheit Scoring: Pilot-Feedback positiv (kein systematischer „Ergebnisse nicht verlässlich"-Kommentar)

### Phase 4 — vollständiges Produkt, wenn:
- Self-Service-Conversion-Rate: > 30 % der Signups zahlen innerhalb 14 Tagen
- Churn nach 30 Tagen: < 20 %
- NPS der aktiven Kunden: > +20
- Verfügbarkeit Prod: > 99.5 % über 90 Tage
- MRR (Monthly Recurring Revenue): Ziel-Hypothese aus `docs/UNIT_ECONOMICS_HYPOTHESES_V1.md` messbar erreicht oder explizit adjustiert

---

## 8 Nächste Schritte heute

1. ~~**BL-15 konkret angehen**~~ → ✅ Abgeschlossen (Architekturentscheid 2026-03-01).
2. **GTM-Sprint #457 terminieren:** Erste 3–4 Discovery-Gespräche (Segment A: Immobilienbewertung) konkret buchen. Ohne Gespräche kein Go für den Entitlement-Implementierungsstart.
3. **Prod-IaC vorbereiten:** Staging-Umgebung in Terraform vorbereiten; Deploy-Workflow auf Staging erproben.
4. **Async UX Smoke auf Staging:** Sobald Staging live, Async-Job-Lifecycle-Test als Abnahme-Gate dokumentieren.
5. **Intelligence-Qualität-Ticket anlegen:** POI-Abdeckungs-Smoke als eigenes Issue aufsetzen (Baseline-Messung auf 20 Referenz-Adressen).

---

*Dieses Dokument ist eine lebende Planung. Phasen-Exit-Kriterien sind verbindlich; Deliverable-Details können in separaten Issues weiter atomisiert werden. Bei Änderung der Priorität oder eines Blockers ist dieses Dokument zu aktualisieren.*

*Referenz-Schlüsseldokumente:*
- *Vision: `docs/VISION_PRODUCT.md`*
- *GTM-Architektur: `docs/GTM_TO_DB_ARCHITECTURE_V1.md`*
- *Rollout-Plan (Async): `docs/MVP_TO_SCALE_ROLLOUT_PLAN_V1.md`*
- *Pricing-Hypothesen: `docs/PACKAGING_PRICING_HYPOTHESES.md`*
- *Entitlement-Lifecycle: `docs/api/entitlement-billing-lifecycle-v1.md`*
- *Async-Domain-Design: `docs/api/async-analyze-domain-design-v1.md`*
- *BL-15 Readiness: `docs/LEGACY_IAM_USER_READINESS.md`*
