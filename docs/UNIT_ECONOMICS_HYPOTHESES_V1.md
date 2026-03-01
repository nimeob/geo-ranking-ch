> **Diese Datei wurde konsolidiert.** Aktuelle kanonische Version: [GTM.md](GTM.md)

---

# BL-30.1.wp2 — Unit-Economics-Hypothesen je Tier/Segment (v1)

Stand: 2026-03-01  
Issue: #459 (Parent #105)

## Ziel

Ein einheitliches, versionierbares Arbeitsmodell für Unit Economics bereitstellen,
um Preis-/Packaging-Entscheide aus BL-30.1 nachvollziehbar zu machen und
BL-30.2 (Entitlements/Shop) mit wirtschaftlichen Guardrails zu versorgen.

## Scope und Modellgrenzen

- Gilt für die Tiers aus [`docs/PRICING_TIER_LIMIT_MATRIX_V1.md`](./PRICING_TIER_LIMIT_MATRIX_V1.md): **Free / Pro / Business**.
- Preiswerte bleiben **Hypothesenbandbreiten** (kein finales Preisblatt), im Einklang mit [`docs/PACKAGING_PRICING_HYPOTHESES.md`](./PACKAGING_PRICING_HYPOTHESES.md).
- Modelliert werden nur wiederkehrende SaaS-Effekte (MRR, COGS, Marge, CAC-Payback).
- Nicht enthalten: einmalige Setup-Projekte, Enterprise-Sonderverträge, regulatorische Sonderfälle.

## Rechenlogik (v1)

Verwendete Kernformeln:

- `ARPA_monat = Preis_pro_Account`
- `Umsatz_monat = ARPA_monat * aktive_Accounts`
- `COGS_monat = (analysen_monat / 1'000) * cogs_pro_1k + support_kosten_monat`
- `Deckungsbeitrag_monat = Umsatz_monat - COGS_monat`
- `Gross_Margin = Deckungsbeitrag_monat / Umsatz_monat`
- `CAC_Payback_Monate = CAC_pro_Account / Deckungsbeitrag_monat_pro_Account`

Annahmen werden bewusst als Bandbreite geführt, damit WP3 die validierbaren
Kandidaten pro Segment auf robuste Schwellen mappen kann.

## Unit-Economics-Hypothesen je Tier/Segment

### Annahmen pro Tier (Bandbreite)

| Tier | Preis-Hypothese (CHF / Monat) | Analysen / Account / Monat | COGS pro 1k Analysen (CHF) | Supportkosten / Account / Monat (CHF) | Ziel-Gross-Margin (Hyp.) |
|---|---:|---:|---:|---:|---:|
| Free | 0 | 80-250 | 6-12 | 1-3 | N/A (Kostenkorridor statt Marge) |
| Pro | 290-590 | 900-2'500 | 8-16 | 20-45 | 65-80% |
| Business | 590-1'200 | 4'000-15'000 | 10-20 | 60-180 | 60-78% |

### Segment-Schnitt (relative Erwartung)

| Segment | Primäre Tier-Erwartung | Nutzungsintensität | Zahlungsbereitschaft vs. COGS-Risiko | Kernrisiko |
|---|---|---|---|---|
| A (Bewertung/Transaktion) | Pro -> Business | mittel bis hoch | robust, wenn Explainability stabil ist | lange Sales-Zyklen |
| B (Projektentwicklung) | Business | hoch | robust bei klarer Zeitersparnis | hohe Erwartung an Daten-/Outputqualität |
| C (Makler/Beratung) | Pro (teilweise Free->Pro) | niedrig bis mittel | preissensitiver, aber onboardingstark | Churn-Risiko bei schwacher Produktadoption |

## Sensitivitätshebel (für WP3-Experimente)

1. **Usage-Intensität pro Account**
   - stärkster COGS-Treiber im Business-Tier.
2. **Conversion Free -> Pro / Pro -> Business**
   - beeinflusst Gesamtmarge stärker als kleine Preisanpassungen.
3. **Supportlast pro Segment**
   - Segment C kann trotz kleinerer Tickets hohe relative Supportkosten auslösen.
4. **COGS-Bandbreite pro 1k Analysen**
   - relevant für non-basic/deep-lastige Flows.

## Entscheidungsschwellen (Go / Adjust / Stop)

### Tier-Ebene

| Entscheidung | Kriterium Pro/Business | Kriterium Free |
|---|---|---|
| **Go** | Gross-Margin >= 65% und CAC-Payback <= 12 Monate | Free-Kosten pro aktivem Free-Account <= 5 CHF/Monat und Free->Pro Conversion-Signal >= 8% |
| **Adjust** | Gross-Margin 55-64% oder CAC-Payback 13-15 Monate | Kosten 5-8 CHF/Monat oder Conversion-Signal 4-7% |
| **Stop** | Gross-Margin < 55% oder CAC-Payback > 15 Monate | Kosten > 8 CHF/Monat ohne belastbares Conversion-Signal |

### Segment-Ebene (Priorisierung)

- **Segment A/B** bleibt priorisiert, wenn mindestens 2 von 3 Signalen erfüllt sind:
  1. Zahlungsbereitschaft innerhalb Zielbandbreite,
  2. klarer Zeitgewinn-Case,
  3. kein kritischer Capability-Blocker (v. a. Entitlements/G3).
- **Segment C** braucht zusätzlich einen stabilen Onboarding-/Adoptionspfad,
  sonst nur als sekundärer Go-to-Market-Kanal.

## Nachprüfbarkeit und Evidenzpfad

- Sprint-/Interview-Rohdaten: `reports/testing/gtm-validation/<sprint_id>/...`
- Standardisiertes Sprint-Template:
  [`docs/testing/GTM_VALIDATION_SPRINT_TEMPLATE.md`](./testing/GTM_VALIDATION_SPRINT_TEMPLATE.md)
- Entscheidungslog (inkl. Option 1/2/3 Ableitung):
  [`docs/testing/GTM_VALIDATION_DECISION_LOG.md`](./testing/GTM_VALIDATION_DECISION_LOG.md)

## Guardrails / Nicht-Ziele

- Keine produktive Preisfestsetzung in diesem Paket.
- Keine Revenue-Prognose mit Finanzplan-Anspruch.
- Keine technische Entitlement-Durchsetzung (folgt in BL-30.2).

## Nächster Schritt

- ✅ #460: Preisvalidierungs-Experimentkarten + Entscheidungslogik auf Basis der
  oben definierten Hebel und Schwellen umgesetzt; Details in
  [`docs/PRICING_VALIDATION_EXPERIMENT_CARDS_V1.md`](./PRICING_VALIDATION_EXPERIMENT_CARDS_V1.md).
- #461: Konsolidierter Abschluss (wp1/wp2/wp3) + Übergabe an BL-30.2.
