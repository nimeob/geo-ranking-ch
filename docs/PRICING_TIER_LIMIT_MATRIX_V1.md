# BL-30.1.wp1 — Pricing-Tier-/Limit-Matrix v1

Stand: 2026-03-01  
Issue: #458 (Parent #105)

## Ziel

Den bestehenden GTM-Hypothesenstand in eine **implementierungsnahe Pricing-Tier-Matrix** überführen,
sodass BL-30.2 (Entitlements/Feature-Gates) direkt darauf aufsetzen kann.

## Scope

- Tier-Entwurf: **Free / Pro / Business**
- pro Tier klare Limits/Capabilities (API, GUI, Explainability, Support/SLA-Nähe)
- expliziter Add-on-Slot für spätere Entitlement-Steuerung

## Tier-Matrix v1 (Entwurf)

> Preise bleiben in dieser Phase bewusst als Hypothesenbandbreiten aus
> [`docs/PACKAGING_PRICING_HYPOTHESES.md`](./PACKAGING_PRICING_HYPOTHESES.md).

| Tier | Zielprofil | Analyze-Volumen/Monat (Richtwert) | API-Rate-Limit (Richtwert) | Explainability-Tiefe | GUI-Zugang | Support/SLA-Nähe |
|---|---|---:|---:|---|---|---|
| **Free** | Evaluierung / Einzeltests | 250 | 5 req/min | Basis (summary + zentrale Faktoren) | Optional Demo-Ansicht | Best-Effort, keine SLA-Zusage |
| **Pro** | Kleine Teams / operative Nutzung | 5'000 | 60 req/min | Erweitert (Faktorpfade + Source-Hinweise) | Vollzugriff auf GUI-MVP | Reaktionsziel nach Geschäftstag-Prinzip |
| **Business** | Produktionsnahe Team-Setups | 50'000 | 240 req/min | Voll (inkl. erweiterter Diagnose-/Trace-Felder) | Vollzugriff + Team-Workspaces | Priorisierte Unterstützung, verhandelte Zielwerte |

## Capability-/Entitlement-Gates (BL-30.2 Übergabe)

Die folgende Matrix ist bewusst als **vertragliche Vorstruktur** für BL-30.2 formuliert.
Technische Durchsetzung erfolgt erst in BL-30.2.

| Gate | Bedeutung | Free | Pro | Business | Umsetzungspfad |
|---|---|---|---|---|---|
| `entitlement.requests.monthly` | monatliches Analyze-Kontingent | 250 | 5'000 | 50'000 | BL-30.2 Quota-Enforcement |
| `entitlement.requests.rate_limit` | kurzzeitiges Request-Limit | 5/min | 60/min | 240/min | BL-30.2 Runtime-Limiter |
| `capability.explainability.level` | Tiefe der Explainability-Ausgabe | basic | extended | full | BL-30.2 Response-Gating |
| `capability.gui.access` | Zugriff auf GUI-Endpunkte | demo | full | full+workspace | BL-30.2 Feature-Flags |
| `capability.trace.debug` | request_id-Trace-Debug Zugriff | no | optional | yes | BL-30.2 Access-Control |

## Add-ons (v1-Parkplatz, noch nicht aktiv)

- **AI-Deep-Analysis Add-on** (BL-30.3 Vorbereitung): höhere Laufzeit-/Token-Budgets, optional pro Request zuschaltbar.
- **Priority Batch Add-on**: höhere Verarbeitungsgeschwindigkeit für asynchrone Jobs.
- **Advanced Export Add-on**: erweitertes Export-/Integrationsformat für Drittsysteme.

Diese Add-ons bleiben bis BL-30.2/30.3 konzeptionell und dürfen aktuell keine Laufzeitabhängigkeit erzwingen.

## Mapping zu bestehendem GTM-Hypothesenstand

- Segment A/B priorisiert API-fähige Tiers (Pro/Business).
- Segment C priorisiert GUI-nahe Nutzbarkeit (Pro/Business mit GUI-Capability).
- Die finale Preisband-Validierung bleibt Bestandteil der GTM-Experimentphase.

Referenzen:
- [`docs/PACKAGING_PRICING_HYPOTHESES.md`](./PACKAGING_PRICING_HYPOTHESES.md)
- [`docs/testing/GTM_VALIDATION_SPRINT_TEMPLATE.md`](./testing/GTM_VALIDATION_SPRINT_TEMPLATE.md)
- [`docs/testing/GTM_VALIDATION_DECISION_LOG.md`](./testing/GTM_VALIDATION_DECISION_LOG.md)

## Guardrails / Nicht-Ziele

- Keine produktive Billing-Implementierung in diesem Work-Package.
- Keine harte Runtime-Entitlement-Logik in API/UI (Folgearbeit BL-30.2).
- Keine finalen Preisentscheidungen vor Abschluss der GTM-Validierung.

## Nächste Work-Packages

- #459: Unit-Economics-Hypothesen je Tier/Segment strukturieren
- #460: Preisvalidierungs-Experimentkarten + Entscheidungslogik
- #461: Konsolidierter Abschluss + BL-30.2 Übergabe
