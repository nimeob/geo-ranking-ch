# WORKING_MODE_FRICTION_ANALYSIS

## Executive Summary

Der aktuelle Arbeitsmodus zeigt starke Engineering-Disziplin, aber mehrere **prozessuale Reibungen**, die den Weg zu einem verkaufsreifen Produkt bremsen. Der größte Hebel liegt nicht in „mehr Features“, sondern in **verlässlicherer Delivery-Mechanik**: harte Qualitätsgates, reproduzierbare Release-Pfade und weniger operativer Overhead.

Die kritischsten Bremsen sind: (1) optionale Qualitätsgates statt verbindlicher PR-Gates, (2) `dev`-only + manuelle Releases, (3) hoher Koordinationsaufwand durch Issue-/Backlog-Mikrosteuerung, (4) skriptlastige Betriebsführung mit degradierenden Fallbacks, (5) GTM-Hypothesen ohne operationalisierten Lernzyklus.

Für Verkaufsreife (Qualität, Vorhersagbarkeit, Time-to-fix, Betriebssicherheit, Release-Fähigkeit) sind kurzfristig wenige gezielte Eingriffe ausreichend, wenn sie konsequent als Produkt-/Delivery-System umgesetzt werden.

---

## Beobachtete hemmende Arbeitsweisen

| # | Hemmende Arbeitsweise (echter Hebel) | Repo-Evidenz (Datei/Prozess/Beispiel) | Risikoauswirkung auf Verkaufsreife | Konkreter Verbesserungsvorschlag (priorisiert) |
|---|---|---|---|---|
| 1 | **Qualitätsprüfung ist optionalisiert** (manuelle/fallback CI statt harter PR-Gates) | `.github/workflows/deploy.yml:4`, `contract-tests.yml:4`, `crawler-regression.yml:4`, `docs-quality.yml:4` jeweils `workflow_dispatch`; `docs/OPERATIONS.md:337` markiert `contract-tests`, `crawler-regression`, `docs-quality` explizit als **nicht required**; `docs/automation/openclaw-job-mapping.md:54` nennt PR-Parität über „Surrogate-Läufe“. | Erhöhtes Risiko, dass Regressionen erst nach Merge/Deploy auffallen; sinkende Vorhersagbarkeit der Delivery; längere Time-to-fix im Incident-Fall. | **P0:** Zwei verpflichtende Fast-Checks auf PR (`contract-smoke`, `docs-links`) wieder automatisch laufen lassen (max. ~8 min). Heavy Checks (Crawler etc.) dürfen weiterhin zeitgesteuert bleiben. |
| 2 | **Release-Fähigkeit bleibt dev-zentriert und manuell** | `README.md:19` („ausschließlich dev“), `README.md` Badge „CI/CD ... manual“; `docs/ENV_PROMOTION_STRATEGY.md:92` Strategie „vorbereitet, aber nicht produktiv aktiviert“; Deploy nur via `workflow_dispatch`. | Kein verlässlicher Pre-Prod-Nachweis, unscharfe Release-Zusagen gegenüber Kunden, höheres Rollout-Risiko bei produktionsnahen Änderungen. | **P0:** „Staging-lite“ als verpflichtendes Zwischen-Gate einführen (gleiches Image-Digest, identische Smokes, dokumentierter Promote/Abort). |
| 3 | **Hoher Prozess-/Dokumentations-Overhead im Tagesbetrieb** | `docs/BACKLOG.md` ist sehr groß (692 Zeilen) mit vielen administrativen Sync-Einträgen (`Checklist-/Issue-Sync`, `Crawler-Reopen`); `worker-claim-priority.yml` setzt Labels automatisiert auf `status:blocked` (`.github/workflows/worker-claim-priority.yml:77-92`); Git-Historie-Auswertung (letzte 200 Commits): `docs` in 187 Commits, `src` in 35, `docs/BACKLOG.md` in 175 Commits. | Delivery-Kapazität fließt in Statuspflege statt in Produkt- und Stabilitätsverbesserung; längere Lead Time; Prioritätenwechsel werden administrativ statt wertorientiert gesteuert. | **P1:** Backlog-Führung verschlanken (Now/Next/Later), Status-Sync automatisiert aus Labels/PR-State generieren, manuelle Checklist-Synchronisation auf Ausnahmen begrenzen. |
| 4 | **Skriptlandschaft ist breit und teils fragil (degradierende Fallbacks)** | 48 operative Skripte unter `scripts/` (30 Shell, 18 Python); `scripts/check_docs_quality_gate.sh:37-42` erlaubt Fallback „PASS ohne frisches venv“; `reports/automation/docs-quality/latest.json` zeigt realen Fallback wegen fehlendem `ensurepip`. | „False Green“-Gefahr bei Qualitätsgates, hoher Onboarding-/Bus-Factor, inkonsistente Time-to-fix durch unterschiedliche Toolpfade und Umgebungsabhängigkeiten. | **P0/P1:** Kritische Gates fail-closed machen (kein stilles PASS bei degradiertem Setup), Skripte in Tier-1 (release-kritisch) vs. Tier-2 (hilfreich) klassifizieren und standardisieren. |
| 5 | **GTM-Lernschleife ist dokumentiert, aber noch nicht in den Delivery-Loop integriert** | `docs/GO_TO_MARKET_MVP.md:38` (Out of Scope: kein finales Pricing), `:97-100` (Pilot/Interview als nächster Schritt); `docs/PACKAGING_PRICING_HYPOTHESES.md:39` (Hypothesenbandbreiten), `:51` (10 Discovery/Pricing-Gespräche); `docs/BACKLOG.md:527` markiert Validierungssprint als nächster offener Schritt. | Risiko von Feature-Arbeit ohne belastbare Zahlungs-/Segmentvalidierung; Produkt kann technisch reifer werden als kommerziell anschlussfähig. | **P1:** Validierungssprint als harte Produkt-Gate in den Backlog-Takt aufnehmen (Interview-Signale -> priorisierte BL-30-Issues mit DoD). |

---

## Konkrete Verbesserungsvorschläge

### Quick Wins (1–2 Wochen)

1. **PR-Gates härten (P0)**
   - Pflichtchecks auf PR: `contract-smoke` + `docs-link-guard`.
   - Ziel: Regressionen vor Merge stoppen, nicht erst in dev.

2. **Degraded-PASS bei Qualitätsgates entfernen (P0)**
   - `check_docs_quality_gate.sh` fail-closed bei fehlender reproduzierbarer Umgebung.
   - Ziel: kein „grün trotz kaputter Umgebung“.

3. **Release-Checkliste mit „staging-lite“-Gate ergänzen (P0)**
   - Ein zusätzlicher verpflichtender Promote-Schritt mit fixem Digest und identischen Smokes.
   - Ziel: höhere Vorhersagbarkeit vor kundenrelevanten Demos/Rollouts.

4. **Backlog-Statuspflege entschlacken (P1)**
   - Wöchentlicher statt kontinuierlicher Checklist-Sync; Auto-Status aus Issue-Labels/PR-Merge.
   - Ziel: weniger Admin-Arbeit, mehr Build-/Fix-Zeit.

5. **GTM-Sprint operationalisieren (P1)**
   - 10 Gespräche aus Hypothesen-Doku terminieren, Signale strukturiert erfassen, Ergebnis als Priorisierungsinput in BL-30 übernehmen.
   - Ziel: Engineering-Roadmap an Zahlungs-/Segmentrealität koppeln.

### Systemische Änderungen (1–2 Monate)

1. **Zwei-Ebenen-Delivery-System etablieren (P0)**
   - Ebene A: schnelle, verpflichtende PR-Checks.
   - Ebene B: tiefere zeitgesteuerte Regressionen + trendbasierte Beobachtung.
   - Ergebnis: Qualität + Geschwindigkeit ohne Overhead-Explosion.

2. **Release-Management von „manuell/dev-only“ zu „promotable“ entwickeln (P0)**
   - Umgebungs- und Freigabelogik auf Digest-Promotion, klaren Rollback und Abnahmebelegen standardisieren.
   - Ergebnis: belastbare Release-Fähigkeit für Sales/Operations.

3. **Tooling-Konsolidierung (P1)**
   - 48 Skripte in wenige produktive „Golden Paths“ überführen (Build/Test/Deploy/Incident).
   - Jede kritische Pipeline mit Owner, SLO und Testabdeckung.

4. **Lean Product Ops einführen (P1)**
   - Backlog in Outcome-orientierte Streams statt reinen Statusfluss trennen.
   - KPI-Set: Lead Time, Change Failure Rate, MTTR, % administrativer Commits.

5. **Commercial Readiness Gate pro Quartal (P1)**
   - Keine größeren Delivery-Epics ohne aktualisierte Marktvalidierung und Segmententscheidung.
   - Ergebnis: technische Arbeit bleibt verkaufsrelevant.

---

## Priorisierte Next Steps (Top 5)

1. **[P0] Pflicht-PR-Gates aktivieren** (`contract-smoke`, `docs-link-guard`) und in Branch-Protection als required setzen.
2. **[P0] Degraded-Fallbacks in kritischen Qualitätschecks entfernen** (insb. Docs-Quality-Gate).
3. **[P0] Staging-lite Promote-Gate einführen** (Digest-basiert, reproduzierbarer Smoke, klarer Abort/Rollback).
4. **[P1] Backlog-/Issue-Prozess auf Lean-Modus umstellen** (Now/Next/Later + automatischer Statussync, weniger manuelle Checklist-Reconciliation).
5. **[P1] GTM-Validierungssprint sofort ausführen und BL-30 priorisieren** (Interview-Signale in konkrete Capability-/Pricing-Entscheidungen überführen).

---

### Kurzfazit

Das Projekt hat eine starke Dokumentations- und Stabilitätsbasis. Der Engpass zur Verkaufsreife liegt aktuell primär in **Delivery-Governance und Prozessfokus**, nicht in fehlender technischer Aktivität. Wenn die fünf Next Steps umgesetzt werden, steigen Vorhersagbarkeit, Release-Vertrauen und kommerzielle Anschlussfähigkeit deutlich.