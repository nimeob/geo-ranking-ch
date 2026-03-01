> **Diese Datei wurde konsolidiert.** Aktuelle kanonische Version: [BACKLOG.md](BACKLOG.md)

---

# BL-30.1.wp4 — Konsolidierter Abschluss + BL-30.2 Übergabe (v1)

Stand: 2026-03-01  
Issue: #461 (Parent #105)

## Ziel

Die Ergebnisse aus BL-30.1.wp1/wp2/wp3 zusammenführen, eine klare
Priorisierung für den nächsten Umsetzungszyklus ableiten und BL-30.2 mit
konkreten, atomaren Folgepaketen versorgen.

## Konsolidierte Eingangsartefakte

- Tier-/Limit-Matrix: [`docs/PRICING_TIER_LIMIT_MATRIX_V1.md`](./PRICING_TIER_LIMIT_MATRIX_V1.md)
- Unit-Economics-Hypothesen: [`docs/UNIT_ECONOMICS_HYPOTHESES_V1.md`](./UNIT_ECONOMICS_HYPOTHESES_V1.md)
- Experimentkarten + Entscheidungslogik: [`docs/PRICING_VALIDATION_EXPERIMENT_CARDS_V1.md`](./PRICING_VALIDATION_EXPERIMENT_CARDS_V1.md)
- Decision-Log (Gate): [`docs/testing/GTM_VALIDATION_DECISION_LOG.md`](./testing/GTM_VALIDATION_DECISION_LOG.md)

## Konsolidierte Empfehlung (BL-30.1 Abschluss)

### Primärkandidat

- **`CAND-API-PRO-390`**
- Begründung:
  1. geringstes Implementierungsrisiko, da API-first auf bestehendem Contract-Unterbau aufsetzt,
  2. passt zur Tier-/Gate-Struktur aus wp1,
  3. liegt innerhalb der in wp2 definierten Pro-Margen-/Payback-Leitplanken.

### Sekundärkandidat

- **`CAND-BIZ-API-890`**
- Begründung:
  1. attraktiver Upside für Segment B,
  2. aber höheres Capability-/Lifecycle-Risiko (Entitlement-/Billing-Tiefe) vor operativer Freigabe.

## Übergaberegel zu BL-30.2

- BL-30.2 wird als **Leaf-Track** vorbereitet (kein Big-Bang),
  aber bleibt bis GTM-Freigabe in #457 blockiert.
- Nach Freigabe gilt oldest-first innerhalb der unblocked Leaves.

### Angelegte BL-30.2 Follow-ups

- #465 — Entitlement-Contract v1 + Gate-Semantik aus BL-30.1 konsolidieren
- #466 — Checkout-/Lifecycle-Contract + idempotenter Entitlement-Sync

## Definition-of-Done-Check (#461)

- [x] Ergebnisse aus wp1/wp2/wp3 zusammengeführt
- [x] Finale Empfehlung (Primär-/Sekundärkandidat) dokumentiert
- [x] BL-30.2-relevante Folgeaufgaben explizit referenziert/erstellt (#465/#466)
- [x] Parent-Sync vorbereitet (#105 Abschlusssektion + #106 Work-Packages)

## Guardrails

- Keine finale Preisfestsetzung ohne GTM-Evidenzlauf.
- Keine produktive Billing-/Checkout-Implementierung in BL-30.1.
- Additive Contract-Evolution (kein Rebuild) bleibt verpflichtend.
