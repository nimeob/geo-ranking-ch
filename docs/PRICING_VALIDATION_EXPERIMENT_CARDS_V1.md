> **Diese Datei wurde konsolidiert.** Aktuelle kanonische Version: [GTM.md](GTM.md)

---

# BL-30.1.wp3 — Preisvalidierungs-Experimentkarten + Entscheidungslogik (v1)

Stand: 2026-03-01  
Issue: #460 (Parent #105)

## Ziel

Die Pricing-/Packaging-Hypothesen aus:

- [`docs/PRICING_TIER_LIMIT_MATRIX_V1.md`](./PRICING_TIER_LIMIT_MATRIX_V1.md)
- [`docs/UNIT_ECONOMICS_HYPOTHESES_V1.md`](./UNIT_ECONOMICS_HYPOTHESES_V1.md)

werden in **experimentfähige Karten** überführt, damit der GTM-Sprint pro Kandidat eine
vergleichbare Go/Adjust/Stop-Entscheidung erzeugt.

## Inputs, Outputs und Run-Konvention

### Pflicht-Inputs je Kandidat

1. **Tier-/Capability-Referenz** (Free/Pro/Business + relevante Gates)
2. **Preiskorridor-Hypothese** (CHF/Monat)
3. **Zielsegmente** (A/B/C)
4. **Unit-Economics-Annahmen** (Marge, CAC-Payback, COGS-Risiken)
5. **Interview-/Signalplan** (min. Stichprobe, kritische Gegenfragen)

### Pflicht-Outputs je Kandidat

- normalisierte Signal-Summary (`go/adjust/stop` pro Gespräch)
- aggregierte Messwerte je Entscheidungskriterium
- finale Kandidatenentscheidung (`GO`, `ADJUST`, `STOP`) mit Begründung
- daraus abgeleitete Follow-up-Issues (BL-30.1 und/oder BL-30.2)

### Artefaktpfade

- Sprint-Rohdaten: `reports/testing/gtm-validation/<sprint_id>/interviews/`
- Sprint-Summary: `reports/testing/gtm-validation/<sprint_id>/summary.md`
- Decision-Log: [`docs/testing/GTM_VALIDATION_DECISION_LOG.md`](./testing/GTM_VALIDATION_DECISION_LOG.md)
- Follow-up-Issue-Template: [`docs/testing/BL30_FOLLOWUP_ISSUE_TEMPLATE.md`](./testing/BL30_FOLLOWUP_ISSUE_TEMPLATE.md)

## Experimentkarte 1 — CAND-API-PRO-390

- **Hypothese:** Ein API-first-Pro-Angebot im Bereich **CHF 390/Monat** erreicht bei Segment A/C ausreichende Zahlungsbereitschaft ohne untragbare Supportlast.
- **Angebotszuschnitt:** Pro-Tier (`capability.explainability.level=extended`, GUI optional)
- **Zielsegmente:** A (primär), C (sekundär)

### Messplan (Signale + Schwellen)

| Kriterium | Messwert | GO | ADJUST | STOP |
|---|---|---:|---:|---:|
| Preisakzeptanz | Anteil Interviews ohne Hard-Reject | >= 60% | 40-59% | < 40% |
| Paket-Fit | `api_only` oder `gui_api` mit Pro-Fit | >= 55% | 35-54% | < 35% |
| Unit-Economics-Gate | Pro-Marge + Payback aus WP2 | Marge >= 65% & Payback <= 12M | Marge 55-64% oder Payback 13-15M | Marge < 55% oder Payback > 15M |
| Kritische Blocker | Anteil `critical_blocker!=none` | <= 20% | 21-35% | > 35% |

### Abbruchkriterien

- Nach den ersten 4 Interviews bereits >= 3 Hard-Rejects im Preiskorridor.
- Entitlement-/Trust-Blocker in > 50% der Gespräche (früher Stop/Adjust statt Vollsprint).

## Experimentkarte 2 — CAND-BIZ-API-890

- **Hypothese:** Ein Business-API-Paket im Bereich **CHF 890/Monat** ist für Segment B tragfähig, wenn Zeitgewinn + Explainability als klarer ROI wahrgenommen werden.
- **Angebotszuschnitt:** Business-Tier (`capability.explainability.level=full`, Team-Workspaces)
- **Zielsegmente:** B (primär), A (sekundär)

### Messplan (Signale + Schwellen)

| Kriterium | Messwert | GO | ADJUST | STOP |
|---|---|---:|---:|---:|
| Preisakzeptanz | Anteil Interviews ohne Hard-Reject | >= 55% | 35-54% | < 35% |
| ROI-Signal | "Zeitgewinn rechtfertigt Preis" bestätigt | >= 50% | 30-49% | < 30% |
| Unit-Economics-Gate | Business-Marge + Payback aus WP2 | Marge >= 62% & Payback <= 12M | Marge 55-61% oder Payback 13-15M | Marge < 55% oder Payback > 15M |
| Capability-Lücke | Anteil fehlender Must-have-Fähigkeiten | <= 20% | 21-35% | > 35% |

### Abbruchkriterien

- Wiederholtes Signal "zu teuer ohne klaren Mehrwert" in >= 3 aufeinanderfolgenden Gesprächen.
- Fehlende Capability-Gates (v. a. Entitlement/Export) blockieren > 40% der B-Interviews.

## Experimentkarte 3 — CAND-GUI-TEAM-590

- **Hypothese:** Ein GUI+API-Team-Paket im Bereich **CHF 590/Monat** reduziert Friktion in Segment C genug, um Conversion gegenüber API-only zu verbessern.
- **Angebotszuschnitt:** Pro/Business-hybrider Team-Plan mit GUI-first Onboarding
- **Zielsegmente:** C (primär), A (sekundär)

### Messplan (Signale + Schwellen)

| Kriterium | Messwert | GO | ADJUST | STOP |
|---|---|---:|---:|---:|
| Paketpräferenz | Anteil `gui_api` als bevorzugtes Modell | >= 60% | 40-59% | < 40% |
| Preisfit | "prüfbar" im Korridor CHF 590 | >= 50% | 30-49% | < 30% |
| Free->Paid-Signal | erkennbares Upgrade-Interesse aus C | >= 20% | 10-19% | < 10% |
| Supportrisiko | erwartete Supportlast vs. Teambandbreite | tragbar im Zielkorridor | beobachtbar erhöht | klar untragbar |

### Abbruchkriterien

- Segment C priorisiert wiederholt API-only trotz GUI-Demo (>= 4 Fälle).
- Onboarding-/Adoptionsfriktion bleibt "hoch" in > 50% der C-Gespräche.

## Standardisierte Entscheidungslogik (Go / Adjust / Stop)

### Regel je Kandidat

- **GO:** mindestens 3 von 4 Kriterien im GO-Bereich und kein STOP-Kriterium.
- **ADJUST:** kein Stop-Kriterium, aber < 3 GO-Kriterien; Kandidat bleibt im Rennen mit klarer Anpassungshypothese.
- **STOP:** mindestens 1 Kriterium im STOP-Bereich oder Abbruchkriterium ausgelöst.

### Pflichtausgabe pro Kandidat (Decision Output Contract)

```yaml
candidate_id: CAND-...
decision: GO|ADJUST|STOP
evidence:
  sprint_id: gtm-validation-...
  interviews_total: <n>
  metric_summary:
    acceptance_rate: <0-1>
    package_fit_rate: <0-1>
    blocker_rate: <0-1>
rationale:
  - <kurzer Grund 1>
  - <kurzer Grund 2>
follow_ups:
  - stream: BL-30.1|BL-30.2
    action: create_issue|update_issue
    issue_ref: <#id oder tbd>
```

Die Follow-up-Erstellung erfolgt mit:
[`docs/testing/BL30_FOLLOWUP_ISSUE_TEMPLATE.md`](./testing/BL30_FOLLOWUP_ISSUE_TEMPLATE.md).

## BL-30.1/BL-30.2 Ableitungsregel

- **Primärkandidat = GO** -> in #461 als BL-30.1-Empfehlung verankern.
- **BL-30.2-Impact vorhanden** (Entitlements, Checkout, Rollen/Quotas) -> sofort Follow-up-Issue nach Template erstellen.
- **Nur ADJUST/STOP-Signale** -> BL-30.1 Anpassungs-Issue erstellen, BL-30.2 nicht als "ready" markieren.

## Guardrails / Nicht-Ziele

- Keine finale Preisfestsetzung in WP3.
- Keine produktive Entitlement-/Checkout-Implementierung in WP3.
- Keine Umpriorisierung außerhalb BL-30 ohne Decision-Log-Evidenz.

## Nächster Schritt

- #461: Konsolidierter Abschluss (wp1/wp2/wp3 zusammenführen) + Übergabe an BL-30.2.
