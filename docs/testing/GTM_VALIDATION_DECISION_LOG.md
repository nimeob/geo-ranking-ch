# GTM Validation Decision Log (BL-341.wp5)

Stand: 2026-03-01  
Bezug: #448, `docs/testing/GTM_VALIDATION_SPRINT_TEMPLATE.md`

## Log-Regeln

- Jeder Eintrag referenziert konkrete Evidenz (Dokument/Interview/Sprint-Output)
- Entscheidungen sind nur gültig mit klarer BL-30-Auswirkung
- Verworfene Optionen müssen explizit begründet werden

## Entscheidungen

| Datum (UTC) | Decision-ID | Evidenz | Entscheidung | BL-30-Auswirkung | Owner | Status |
|---|---|---|---|---|---|---|
| 2026-03-01 | GTM-DEC-001 (Seed) | `docs/PACKAGING_PRICING_HYPOTHESES.md` (10-Interview-Design + Option 1/2/3), `docs/testing/WORKING_MODE_FRICTION_ANALYSIS.md` (P1-Finding zur fehlenden GTM-Lernschleife), Capability-Gates G1/G2=verfügbar, G3=offen | **Validierungssprint als harte Freigabestufe vor BL-30-Unblocking**. Vor Abschluss eines dokumentierten 10er-Sprints bleibt BL-30.1/30.2 in `status:blocked`. | Nach Sprintabschluss wird BL-30-Reihenfolge aus den Signalen abgeleitet: Option 1 -> BL-30.1 zuerst, Option 2 -> BL-30.2 priorisiert, Option 3 -> Parallelisierung mit Capacity-Limit. | Product/Backlog Owner | accepted |
| 2026-03-01 | GTM-IN-30.3-001 (Input) | `docs/DEEP_MODE_ADDON_QUOTA_HYPOTHESES_V1.md` (DM-H1..DM-H4, Quota-/Transparenzrahmen), `docs/api/deep-mode-contract-v1.md`, `docs/api/deep-mode-orchestration-guardrails-v1.md` | Deep-Mode Add-on wird als **validierungspflichtiger Kandidat** in den GTM-Sprint eingebracht; Entscheidung erst nach Evidenz (`GTM-DEC-002`). | #457 erhält ein verbindliches Bewertungsset (`requested/effective/fallback_reason/quota_*`) zur Go/Adjust/Stop-Ableitung für BL-30.3 und das Entitlement-Design in BL-30.2. | Product/Backlog Owner | ready-for-validation |
| 2026-03-01 | GTM-DEC-002 | `reports/testing/gtm-validation/gtm-validation-001/summary.md` (konsolidierter 60-Fragen-Antwortsatz im Sprint-Raster), `docs/PACKAGING_PRICING_HYPOTHESES.md`, `docs/PRICING_VALIDATION_EXPERIMENT_CARDS_V1.md` | **Option 2 priorisieren**: BL-30.2 wird nach Abschluss von BL-30.1 als nächster Monetization-Track umgesetzt; Option 1 = Adjust, Option 3 = Stop (aktuell). | GTM-Gate für #457 gilt als erfüllt; BL-30.2-Leaf-Reihenfolge wird entblockt (`#465 -> #466`), Parent #106 auf ausführbar synchronisieren, Parent #128 entsprechend nachziehen. | Product/Backlog Owner | accepted |

## Folgeaktion aus GTM-DEC-001 (Status)

1. ✅ Sprint `gtm-validation-001` durchgeführt (konsolidierter Antwortsatz im Sprint-Raster).
2. ✅ Sprint-Summary unter `reports/testing/gtm-validation/gtm-validation-001/summary.md` abgelegt.
3. ✅ Folgeentscheidung `GTM-DEC-002` mit konkreter Option + BL-30-Issue-Umpriorisierung eingetragen.
