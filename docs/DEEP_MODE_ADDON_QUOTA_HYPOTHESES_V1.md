# BL-30.3.wp3 — Deep-Mode Add-on-/Quota-Hypothesen + Transparenzrahmen (v1)

Stand: 2026-03-01  
Issue: #470 (Parent #107)

## Ziel

Für BL-30.3 einen produktnahen, testbaren Rahmen liefern, damit Deep-Mode als optionales Add-on
nicht nur technisch umsetzbar, sondern auch **messbar vermarktbar** und **transparent kommunizierbar** bleibt.

Dieses Paket ergänzt die technischen Vorarbeiten aus:
- [`docs/api/deep-mode-contract-v1.md`](./api/deep-mode-contract-v1.md)
- [`docs/api/deep-mode-orchestration-guardrails-v1.md`](./api/deep-mode-orchestration-guardrails-v1.md)

## 1) Hypothesenblatt (messbar)

> Alle Werte sind bewusst Hypothesen (kein finales Pricing-Commit).

| ID | Hypothese | Messsignal | Erfolgsschwelle | Stop-/Adjust-Signal |
|---|---|---|---|---|
| DM-H1 (Value) | Segmente A/B akzeptieren Deep-Mode als **optionales Add-on**, wenn die Zusatzanalyse als klar verwertbar erlebt wird. | Interview-/Sprint-Frage: „Würden Sie Deep-Mode pro Run/Monat zusätzlich buchen?“ | >= 60% positive Kaufbereitschaft im Zielsegment bei klarer Problemzuordnung | < 40% Kaufbereitschaft oder wiederholtes „kein Zusatznutzen“ |
| DM-H2 (Quota-Fit) | Ein planbares Quota-Modell wird als fairer wahrgenommen als „unklare AI-Nutzung“. | Anteil Gespräche mit „Quota verständlich/fair“ | >= 70% verstehen Quota-Mechanik ohne zusätzliche Nachfragen | > 30% Verwirrung über Restquota/Verbrauch |
| DM-H3 (Transparenz) | Klare Kennzeichnung AI-generierter Zusatzteile erhöht Vertrauen in Entscheidungen. | Vertrauen-Score (1-5) nach Explainability-Demo | Mittelwert >= 4.0 bei Sichtbarkeit von `effective/fallback_reason` | Mittelwert < 3.5 oder wiederholte Intransparenzkritik |
| DM-H4 (Budgetgrenze) | Soft-Gates (Entitlement + Quota + Budget) reduzieren Kostenangst, ohne den Basispfad zu entwerten. | Anteil Runs mit akzeptiertem Graceful-Downgrade | >= 95% Akzeptanz für Basisergebnis trotz Deep-Fallback | > 10% Beschwerden zu „unerwartetem Downgrade“ |

## 2) Entitlement-/Quota-Kopplung an Contract-Felder

### 2.1 Verbindliche Feldpfade (v1, additiv)

| Produkt-/Quota-Semantik | Request/Response-Feld | Interpretation für Produkt/GTM |
|---|---|---|
| Nutzer fordert Deep-Mode an | `options.capabilities.deep_mode.requested` | Primärer Nachfrageindikator für Add-on-Interesse |
| Gewünschtes Deep-Profil | `options.capabilities.deep_mode.profile` | Segment-/Use-Case-Zuordnung für spätere Paketvarianten |
| Clientseitiger Budgetwunsch | `options.capabilities.deep_mode.max_budget_tokens` | Preis-/Kosten-Sensitivität je Use Case |
| Entitlement-Freigabe | `options.entitlements.deep_mode.allowed` | Harte Produktfreigabe (Plan/Account) |
| Restquota vor Run | `options.entitlements.deep_mode.quota_remaining` | Transparente Erwartung vor Ausführung |
| Effektive Deep-Aktivierung | `result.status.capabilities.deep_mode.effective` | Nachweis, ob Add-on wirklich genutzt wurde |
| Fallback-Grund | `result.status.capabilities.deep_mode.fallback_reason` | Kommunikationsanker für faire Downgrade-UX |
| Quota-Verbrauch im Run | `result.status.entitlements.deep_mode.quota_consumed` | Billing-/Abrechnungsnahe Unit pro Request |
| Restquota nach Run | `result.status.entitlements.deep_mode.quota_remaining` | Basis für Self-Serve-Nachvollziehbarkeit |

### 2.2 Quota-Policy-Rahmen (Hypothesen-v1)

- **Unit:** 1 Deep-Run = 1 Quota-Unit (`quota_consumed=1`), Basispfad bleibt `0`.
- **Reset-Fenster:** monatlich (aligned mit BL-30.1 Tier-Logik).
- **Graceful-Downgrade:** bei `allowed=false` oder `quota_remaining=0` bleibt Basisergebnis verpflichtend erhalten.
- **No Surprise Rule:** `fallback_reason` muss für nicht erfüllte Deep-Anfragen immer gesetzt werden (`not_entitled`, `quota_exhausted`, `timeout_budget`, `policy_guard`, `runtime_error`).

## 3) Transparenzrahmen für AI-generierte Zusatzinhalte

Mindestregeln für Produkt-/Integrationskommunikation:

1. **Sichtbarkeit**: Bei Deep-Anfrage muss das Ergebnis erkennbar machen, ob Deep effektiv war (`effective`).
2. **Grundklarheit**: Bei Downgrade muss der Grund maschinen- und menschenlesbar sein (`fallback_reason`).
3. **Nicht-Verschleierung**: Basisergebnis darf durch Deep-Fallback nie verborgen oder als Fehler maskiert werden.
4. **Auditierbarkeit**: Deep-Laufentscheidungen müssen über strukturierte Events nachvollziehbar bleiben (siehe BL-340 + #473).
5. **Produktclaim-Guard**: Marketing-/Sales-Claims dürfen nur auf Signale basieren, die im Contract/Status tatsächlich beobachtbar sind.

## 4) Entscheidungseingang für GTM-Track

Der WP3-Output wird als formaler Input für den GTM-Entscheidungspfad erfasst:

- Decision-Log-Eintrag: [`docs/testing/GTM_VALIDATION_DECISION_LOG.md`](./testing/GTM_VALIDATION_DECISION_LOG.md) (`GTM-IN-30.3-001`)
- Sprint-/Priorisierungsbezug: #457 (`BL-341.wp5.r1`)

### Erwartete Nutzung im Sprint `gtm-validation-001`

- DM-H1 bis DM-H4 werden als Pflicht-Frage-/Bewertungsset in die Interviewauswertung übernommen.
- `requested/effective/fallback_reason/quota_*` dienen als Referenzfelder für die Ableitung
  von Go/Adjust/Stop für ein Deep-Mode-Add-on.
- Finaler Produktentscheid bleibt bei `GTM-DEC-002` (nach evidenzbasiertem Sprintabschluss).

## 5) Nicht-Ziele (wp3)

- Keine Runtime-Implementierung des Orchestrators (siehe #472).
- Keine Telemetrie-Implementierung inkl. Trace-Evidence in Code/Runbook (siehe #473).
- Keine finale Preisfestlegung vor Abschluss von `gtm-validation-001`.

## 6) Follow-up nach wp3

- #472 — Deep-Mode Runtime-Orchestrator im `/analyze`-Flow implementieren
- #473 — Deep-Mode-Telemetrie + Trace-Evidence absichern
- #457 — GTM-Validierung durchführen und BL-30-Entscheidung ableiten
