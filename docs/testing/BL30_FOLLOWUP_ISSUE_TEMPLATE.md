> **Diese Datei wurde konsolidiert.** Aktuelle kanonische Version: [RUNBOOKS.md](RUNBOOKS.md)

---

# BL-30 Follow-up-Issue Template (aus GTM-/Pricing-Entscheidungen)

Stand: 2026-03-01  
Bezug: #460, [`docs/PRICING_VALIDATION_EXPERIMENT_CARDS_V1.md`](../PRICING_VALIDATION_EXPERIMENT_CARDS_V1.md)

## Zweck

Standardisiertes Schema, um Entscheidungen aus GTM-/Pricing-Experimenten konsistent in
**BL-30.1 (Pricing/Packaging-Fortschreibung)** und **BL-30.2 (Entitlements/Shop)** zu überführen.

## Pflicht-Labels

- `backlog`
- `priority:P1|P2|P3` (kontextabhängig)
- `status:todo` (oder `status:blocked` mit klarer Abhängigkeit)

## Template: BL-30.1 Follow-up (Pricing/Packaging)

```markdown
## Kontext
Ableitung aus Decision-Log `<decision-id>` und Kandidat `<candidate-id>`.
Parent: #105 (BL-30.1)

## Problem
<welche Pricing-/Packaging-Annahme ist unzureichend oder zu schärfen?>

## Scope
- <klarer Arbeitspunkt 1>
- <klarer Arbeitspunkt 2>
- <klarer Arbeitspunkt 3>

## Definition of Done
- [ ] Anpassung in relevanter Pricing-Doku durchgeführt
- [ ] Entscheidungsbezug (Decision-Log + Evidenz) verlinkt
- [ ] Folgeauswirkung auf BL-30.2 explizit bewertet (ja/nein + Begründung)
- [ ] Doku-/Link-Checks grün

## Abhängigkeiten
- Decision-Log: `docs/testing/GTM_VALIDATION_DECISION_LOG.md#<anchor>`
- Evidenz: `reports/testing/gtm-validation/<sprint_id>/summary.md`
```

## Template: BL-30.2 Follow-up (Entitlements/Checkout)

```markdown
## Kontext
Ableitung aus Decision-Log `<decision-id>` und Kandidat `<candidate-id>`.
Parent: #128 (BL-30) / Zielstream: #106 (BL-30.2)

## Problem
<welcher Entitlement-/Checkout- oder Lifecycle-Teil muss konkretisiert/umgesetzt werden?>

## Scope
- <Quota/Feature-Gate oder Produktkatalog-Punkt>
- <Checkout/Subscription-Lifecycle-Punkt>
- <Contract-/Runtime-Auswirkung>

## Definition of Done
- [ ] Technischer Entitlement-/Billing-Scope eindeutig beschrieben
- [ ] Contract-/API-Auswirkungen dokumentiert
- [ ] Guardrails zu BL-20 Forward-Compatibility explizit referenziert
- [ ] Test-/Doku-Nachweis geplant oder umgesetzt

## Abhängigkeiten
- BL-30.1 Referenz (Primärentscheidung): #105 / #461
- Decision-Log: `docs/testing/GTM_VALIDATION_DECISION_LOG.md#<anchor>`
```

## Erstellungskonvention

Beim Anlegen eines Follow-up-Issues immer zusätzlich im auslösenden Issue dokumentieren:

- `Follow-up: #<neu>`
- `Grund: <1 Satz>`
- `Abhängigkeit: <Decision-ID / Sprint-ID>`

So bleibt die Kette **Experiment -> Entscheidung -> Umsetzung** auditierbar.
