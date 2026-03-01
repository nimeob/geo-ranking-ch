# GTM — Go-to-Market, Pricing & Monetization (kanonisch)

> Dieses Dokument ist der **kanonische Ort** für alle GTM/Monetization-Inhalte.
> Die Quell-Dokumente bleiben aus Kompatibilitätsgründen erhalten; neue Ergänzungen gehören hierher.

Stand: 2026-03-01

---

## 1) Value Proposition & Zielsegmente

*Quelle: [`docs/GO_TO_MARKET_MVP.md`](GO_TO_MARKET_MVP.md) — BL-20.7.b*

**Problem:** Standort- und Gebäudeentscheidungen in der Schweiz erfordern manuelle Recherche über viele fragmentierte Quellen.

**Nutzenversprechen:** Geo Ranking CH liefert in wenigen Sekunden eine nachvollziehbare Standort-/Gebäudeeinschätzung pro Adresse oder Kartenpunkt — inklusive Quellen, Aktualität und Confidence.

### Zielsegmente (MVP)
- **A — Immobilienbewertung/Transaktionsvorbereitung:** Zeitgewinn, Explainability, Vergleichbarkeit
- **B — Projektentwicklung/Bauvorprüfung:** Frühindikatoren, Risiko-Früherkennung, Szenario-Vergleiche
- **C — Makler-/Beratungs-Workflows:** sofort nutzbares Frontend, Demo-/Meeting-Tauglichkeit

### Angebotsrahmen (MVP)
- **API-only:** B2B/Integrations-Fokus, stabile Schnittstelle, Explainability-Felder
- **GUI+API:** Endnutzer-/Beratungs-Fokus, schnelle Nutzbarkeit, Demo-Fähigkeit

---

## 2) Packaging-Hypothesen je Segment

*Quelle: [`docs/PACKAGING_PRICING_HYPOTHESES.md`](PACKAGING_PRICING_HYPOTHESES.md) — BL-20.7.r3*

| Segment | Hypothese | Angebotszuschnitt | Preisannahme (CHF/Monat) | Erfolgsschwelle |
|---|---|---|---|---|
| A (Bewertung) | Teams akzeptieren monatliches Abo statt Pay-per-report | API-only inkl. `/analyze`, Explainability, Basis-SLA | 290–590 / Team | >= 3/5 Gespräche: Abo bevorzugt |
| B (Projektentwicklung) | Höherer Preis für schnellere Vorprüfung wird akzeptiert | API-only Plus (höhere Limits, exportfähig) | 590–1'200 / Team | >= 2/4 Teams: Zeitgewinn rechtfertigt Preis |
| C (Makler/Beratung) | Seat-/Workspace-Modell verständlicher als reiner API-Preis | GUI+API inkl. Ergebnisdarstellung | 49–119 / Nutzer oder 390–890 / Team | >= 60% bevorzugen GUI-Paket |

---

## 3) Tier-Matrix v1 (Free / Pro / Business)

*Quelle: [`docs/PRICING_TIER_LIMIT_MATRIX_V1.md`](PRICING_TIER_LIMIT_MATRIX_V1.md) — BL-30.1.wp1*

| Tier | Zielprofil | Analysen/Monat | Rate-Limit | Explainability | GUI | SLA |
|---|---|---:|---:|---|---|---|
| **Free** | Evaluierung | 250 | 5 req/min | Basis | Demo-Ansicht | Best-Effort |
| **Pro** | Kleine Teams | 5'000 | 60 req/min | Erweitert | Vollzugriff | Geschäftstag |
| **Business** | Produktionsnahe Teams | 50'000 | 240 req/min | Voll + Trace | Vollzugriff + Workspaces | Priorisiert |

### Capability-/Entitlement-Gates (BL-30.2 Übergabe)

| Gate | Free | Pro | Business |
|---|---|---|---|
| `entitlement.requests.monthly` | 250 | 5'000 | 50'000 |
| `entitlement.requests.rate_limit` | 5/min | 60/min | 240/min |
| `capability.explainability.level` | basic | extended | full |
| `capability.gui.access` | demo | full | full+workspace |
| `capability.trace.debug` | no | optional | yes |

---

## 4) Unit-Economics-Hypothesen (v1)

*Quelle: [`docs/UNIT_ECONOMICS_HYPOTHESES_V1.md`](UNIT_ECONOMICS_HYPOTHESES_V1.md) — BL-30.1.wp2*

### Annahmen pro Tier (Bandbreite)

| Tier | Preis (CHF/Monat) | Analysen/Account | COGS/1k (CHF) | Support/Account (CHF) | Ziel-Gross-Margin |
|---|---:|---:|---:|---:|---:|
| Free | 0 | 80–250 | 6–12 | 1–3 | N/A |
| Pro | 290–590 | 900–2'500 | 8–16 | 20–45 | 65–80% |
| Business | 590–1'200 | 4'000–15'000 | 10–20 | 60–180 | 60–78% |

### Entscheidungsschwellen (Go / Adjust / Stop)

| Entscheidung | Pro/Business | Free |
|---|---|---|
| **Go** | Gross-Margin >= 65% und CAC-Payback <= 12 Monate | Kosten <= 5 CHF/Account/Monat + Conversion-Signal >= 8% |
| **Adjust** | Marge 55–64% oder Payback 13–15 Monate | Kosten 5–8 CHF oder Signal 4–7% |
| **Stop** | Marge < 55% oder Payback > 15 Monate | Kosten > 8 CHF ohne Signal |

---

## 5) Preisvalidierungs-Experimentkarten (v1)

*Quelle: [`docs/PRICING_VALIDATION_EXPERIMENT_CARDS_V1.md`](PRICING_VALIDATION_EXPERIMENT_CARDS_V1.md) — BL-30.1.wp3*

### Kandidaten

| Kandidat-ID | Hypothese | Tier | Preis (CHF/Monat) | Primärsegment |
|---|---|---|---|---|
| **CAND-API-PRO-390** | API-first Pro bei ~390/Monat erreicht bei Seg. A/C ausreichende Zahlungsbereitschaft | Pro | ~390 | A (primär), C (sekundär) |
| **CAND-BIZ-API-890** | Business-API ~890/Monat ist für Seg. B tragfähig bei klarem ROI | Business | ~890 | B (primär), A (sekundär) |
| **CAND-GUI-TEAM-590** | GUI+API Team-Paket ~590/Monat reduziert Friktion in Seg. C | Pro/Business hybrid | ~590 | C (primär), A (sekundär) |

### Entscheidungslogik

- **GO:** ≥ 3/4 Kriterien im GO-Bereich, kein STOP-Kriterium
- **ADJUST:** kein STOP, aber < 3 GO-Kriterien
- **STOP:** ≥ 1 Kriterium im STOP-Bereich oder Abbruchkriterium ausgelöst

---

## 6) Deep-Mode Add-on — Quota-Hypothesen (v1)

*Quelle: [`docs/DEEP_MODE_ADDON_QUOTA_HYPOTHESES_V1.md`](DEEP_MODE_ADDON_QUOTA_HYPOTHESES_V1.md) — BL-30.3.wp3*

### Hypothesenblatt

| ID | Hypothese | Erfolgsschwelle |
|---|---|---|
| DM-H1 (Value) | Seg. A/B akzeptieren Deep-Mode als optionales Add-on | >= 60% Kaufbereitschaft |
| DM-H2 (Quota-Fit) | Planbares Quota-Modell gilt als fair | >= 70% verstehen Mechanik |
| DM-H3 (Transparenz) | Klare Kennzeichnung AI-generierter Teile erhöht Vertrauen | Mittelwert Vertrauen >= 4.0/5 |
| DM-H4 (Budgetgrenze) | Soft-Gates reduzieren Kostenangst ohne Basispfad zu entwerten | >= 95% Akzeptanz Graceful-Downgrade |

### No Surprise Rule
Bei `allowed=false` oder `quota_remaining=0` muss `fallback_reason` immer gesetzt sein:
`not_entitled | quota_exhausted | timeout_budget | policy_guard | runtime_error`

Technische Details: [`docs/api/deep-mode-contract-v1.md`](api/deep-mode-contract-v1.md)

---

## 7) GTM → Data Architecture Mapping (v1)

*Quelle: [`docs/GTM_TO_DB_ARCHITECTURE_V1.md`](GTM_TO_DB_ARCHITECTURE_V1.md) — Issue #585*

### Kanonisches Kern-Datenmodell v1 (Entitäten)

| Entität | Zweck |
|---|---|
| `organizations` | Primär-Tenant (Org = harte Datengrenze) |
| `users` | Identitäten |
| `memberships` | User-Rolle innerhalb einer Org |
| `plans` | Versioniertes Pricing-/Packaging-Objekt |
| `subscriptions` | Zugewiesener Plan pro Org + Lifecycle |
| `entitlements` | Effektive Capability-/Limit-Werte je Org |
| `usage_counters` | Metering für Limits/Abrechnung |
| `api_keys` | API-Zugriff auf Tenant-Ressourcen |
| `audit_events` | Append-only Nachvollziehbarkeit |

### No-regrets Defaults
- UUID/ULID-IDs, UTC-Timestamps, Soft-Delete via Statusfelder
- Additive Schema-Evolution, normalisierte `entitlements`-Tabelle
- Provider-Abstraktion: `billing_provider` + `provider_reference`

---

## 8) Packaging Baseline (Build/Run)

*Quelle: [`docs/PACKAGING_BASELINE.md`](PACKAGING_BASELINE.md) — BL-20.7.a*

### Build/Run-Matrix

| Modus | Setup | Run | Verify |
|---|---|---|---|
| Lokal (venv) | `python3.12 -m venv .venv && pip install -r requirements-dev.txt` | `python -m src.api.web_service` | `curl -fsS http://127.0.0.1:8080/health` |
| Docker | `docker build -t geo-ranking-ch:dev .` | `docker run --rm -p 8080:8080 geo-ranking-ch:dev` | `curl -fsS http://127.0.0.1:8080/health` |

### Release-Gate (API-only Packaging)

| Check | Kommando | Erwartung |
|---|---|---|
| Build | `pip install -r requirements-dev.txt` | Dependencies ohne Fehler |
| Run | `python -m src.api.web_service` | Startet ohne Traceback |
| Smoke | `curl -fsS http://127.0.0.1:8080/health` | `{"ok": true}` |
| Test-Gate | `pytest tests/test_web_e2e.py -q` | Exit-Code 0 |
| Doku-Check | `./scripts/check_docs_quality_gate.sh` | Exit-Code 0 |

---

## 9) GTM-Validierungs-Links

- Sprint-Template: [`docs/testing/GTM_VALIDATION_SPRINT_TEMPLATE.md`](testing/GTM_VALIDATION_SPRINT_TEMPLATE.md)
- Decision-Log: [`docs/testing/GTM_VALIDATION_DECISION_LOG.md`](testing/GTM_VALIDATION_DECISION_LOG.md)
- Follow-up-Template: [`docs/testing/BL30_FOLLOWUP_ISSUE_TEMPLATE.md`](testing/BL30_FOLLOWUP_ISSUE_TEMPLATE.md)
- Demo-Datenset: [`docs/DEMO_DATASET_CH.md`](DEMO_DATASET_CH.md)
- Lizenz-Gate: [`docs/DATA_SOURCES.md`](DATA_SOURCES.md)
