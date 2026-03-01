# Minimum-Compliance-Set — Kontrollplan Export/Löschung v1

_Status: freigegeben (Repo-Baseline)_  
_Gültig ab: 2026-03-01_  
_Bezug: Issue #518_

## Zweck

Dieser Kontrollplan definiert den **verbindlichen Prüfzyklus** für Export- und Löschprozesse im Projekt `geo-ranking-ch`.
Ziel ist eine reproduzierbare, auditierbare Kontrolle von:

- Exportvorgängen (Wer hat was wann über welchen Kanal exportiert?)
- Löschläufen (wurden Löschkandidaten korrekt und vollständig verarbeitet?)

## Geltungsbereich

- Umgebungen: `dev`, `staging`, `prod`
- Prozessbereiche: Export, Löschung, Hold-bedingte Ausnahmen
- Rollen: `Compliance Lead`, `IT Product Owner`, `Operations`

## Kontrollfrequenz (verbindlich)

| Kontrolltyp | Frequenz | Mindestumfang | Zweck |
|---|---|---|---|
| Export-Kontrolle (Standard) | wöchentlich | Stichprobe `max(10, 10%)` aller Exporte der Woche | Früherkennung unzulässiger Exporte/kanalbezogener Abweichungen |
| Export-Kontrolle (Monatsreview) | monatlich | Stichprobe `max(25, 15%)` inkl. risikobasierter Fälle | Trendanalyse + Wirksamkeitscheck der Export-Governance |
| Löschlauf-Kontrolle (Standard) | wöchentlich | Stichprobe `max(10, 10%)` aller Löschfälle der Woche | Nachweis korrekter und fristgerechter Löschverarbeitung |
| Löschlauf-Kontrolle (Monatsreview) | monatlich | Vollprüfung aller fehlgeschlagenen/abgebrochenen Löschläufe + Stichprobe `max(25, 15%)` erfolgreicher Läufe | Eskalations-/Risikobewertung und Stabilitätsaussage |

## Stichprobenregeln

1. **Kombiniertes Sampling:**
   - Zufallsstichprobe aus der Grundgesamtheit des Kontrollzeitraums
   - plus risikobasierte Zusatzfälle (z. B. privilegierte Rollen, Grenzfälle, ungewöhnliche Volumina)
2. **Risikobasierte Pflichtfälle:**
   - 100% Prüfung aller fehlgeschlagenen Löschläufe
   - 100% Prüfung aller Exporte mit manueller Sonderfreigabe
3. **Reproduzierbarkeit:**
   - Für Zufallsauswahl wird der verwendete Seed dokumentiert (`sampling_seed`)
   - Auswahlkriterien und Filter müssen im Nachweis explizit enthalten sein

## Nachweisformat (verbindlich)

Jeder Kontrolllauf wird als Nachweispaket abgelegt unter:

`reports/compliance/controls/<YYYY>/<MM>/<control_run_id>/`

Pflichtbestandteile pro Kontrolllauf:

| Feld | Pflicht | Beschreibung |
|---|---|---|
| `control_run_id` | ja | Eindeutige ID (`CTRL-<type>-<date>-<seq>`) |
| `control_type` | ja | `export-weekly`, `export-monthly`, `delete-weekly`, `delete-monthly` |
| `period_start` | ja | Start des geprüften Zeitraums (ISO-8601) |
| `period_end` | ja | Ende des geprüften Zeitraums (ISO-8601) |
| `population_size` | ja | Gesamtanzahl Vorgänge im Zeitraum |
| `sample_size` | ja | Anzahl geprüfter Stichprobenfälle |
| `sample_method` | ja | `random`, `risk-based`, `mixed` |
| `sampling_seed` | ja (bei random/mixed) | Seed zur Reproduktion der Auswahl |
| `findings_summary` | ja | Kurzfazit inkl. Abweichungsanzahl |
| `exceptions` | ja | Liste festgestellter Abweichungen inkl. Schweregrad |
| `evidence_links` | ja | Referenzen auf Export-/Löschlogs und Ticketbelege |
| `reviewed_by_role` | ja | Rolle der prüfenden Instanz |
| `reviewed_at` | ja | Review-Zeitpunkt (ISO-8601) |
| `status` | ja | `pass`, `pass-with-findings`, `fail` |

Empfohlenes Dateiset im Nachweispaket:

- `control_summary.md` (menschlich lesbare Zusammenfassung)
- `control_evidence.json` (strukturierter Export für Audits)
- `control_sample.csv` (geprüfte Fälle)
- `exceptions.md` (Detailbeschreibung von Abweichungen/Eskalationen)

## Rollen, Freigabe und Eskalation

1. **Operations** führt den Kontrolllauf aus und erzeugt das Nachweispaket.
2. **Compliance Lead** prüft das Paket und zeichnet die Bewertung (`status`) fachlich ab.
3. **IT Product Owner** bewertet technische Korrekturmaßnahmen bei Findings mit Systembezug.
4. Bei `fail` oder kritischen Findings gilt:
   - Incident-/Follow-up-Issue innerhalb von 1 Arbeitstag
   - Verlinkung des Follow-ups im Nachweispaket (`evidence_links`)
   - erneuter Kontrolllauf nach Umsetzung der Maßnahme

## Abgrenzung / Nicht-Ziele

- Dieser Plan definiert **Governance und Nachweisformat**, nicht die technische Implementierung von Export-/Löschlogik.
- Umsetzungs-Issues bleiben separat:
  - #525 (Export-Logging implementieren)
  - #522 (Lösch-Scheduler mit Vorankündigung)
  - #527 (Abnahmetests für Minimum-Compliance-Set)

## Nachweis

- Backlog-Sync: `docs/BACKLOG.md`
- Umsetzung/Claim-Historie: `https://github.com/nimeob/geo-ranking-ch/issues/518`
