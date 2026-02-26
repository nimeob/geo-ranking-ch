# Autonomous Agent Mode (Nipa)

Dieses Dokument definiert verbindlich, wie Nipa in diesem Repository weiterarbeitet.

## Ziel

- Keine Abhängigkeit von Nico-User-Credentials für GitHub-Operationen
- Komplexe Aufgaben robust mit Subagents bearbeiten
- Parallelisierung nutzen, wenn unabhängig machbar
- Hohe Qualität bei Architektur-/Deploy-/Debug-Themen

## GitHub Auth-Standard (verbindlich)

**Nipa arbeitet mit GitHub App Auth, nicht mit Nico-User-Login.**

Pfad/Wrapper im Repo:

- `scripts/gh_app_token.sh` → mintet on-demand ein GitHub Installation Token
- `scripts/gha` → Wrapper für `gh` mit App-Token (`GH_TOKEN`)
- `scripts/gpush` → Wrapper für `git push` mit App-Token

### Usage

```bash
# GitHub CLI via App-Token
./scripts/gha run list --limit 5
./scripts/gha workflow run deploy.yml

# Push via App-Token
./scripts/gpush
./scripts/gpush origin main
```

## Execution Mode für komplexe Arbeit

Bei komplexen/mehrstufigen Aufgaben gilt:

1. **Subagent-first** mit
   - `model=openai-codex/gpt-5.3-codex`
   - `thinking=high`
2. **Parallelisieren**, wenn Teilaufgaben unabhängig sind (z. B. Analyse + Doku + Testplan).
3. Hauptsession bleibt Koordinator (Plan, Integration, finale Commits).

## Job-Framework (verbindlich) — Drei Säulen pro Feature

Ab sofort wird jede Weiterentwicklung entlang von **3 Säulen** geplant und umgesetzt:

1. **Programmierung** (Feature/Code)
2. **Dokumentation** (User- und Betriebsdoku)
3. **Testing** (Regression + Erweiterung auf neue Features)

Regel: Neue Features gelten erst als „integriert“, wenn alle drei Säulen aktualisiert sind.

### Reihenfolge-Entscheid (Nico-Vorgabe)

- **BL-19 zuerst** auf arbeitsfähigen Stand bringen (Doku-Säule aufholen).
- **BL-20 erst danach** starten.
- Während BL-20 laufen alle 3 Säulen pro Iteration parallel mit.
- **BL-18.1 ist eingefroren (Freeze)**, bis BL-19-MVP abgeschlossen ist.

### BL-18.1 Freeze-Regel (verbindlich)

- Keine neuen BL-18.1-Commits, keine Scope-Erweiterung, keine zusätzlichen Hardening-Loops.
- Erlaubt sind nur:
  1. **kritische Produktionsfixes** (akuter Ausfall/Deployment-Blocker), oder
  2. **explizite Freigabe durch Nico**.
- Bei erlaubten Ausnahmefixes:
  - minimaler Eingriff,
  - kurzer Nachweis im Commit,
  - danach sofort zurück zu BL-19.

### BL-19 Gate vor BL-20 (harte Eintrittsbedingung)

BL-20 startet erst, wenn mindestens folgende BL-19-Teile umgesetzt sind:
- BL-19.1 Informationsarchitektur
- BL-19.2 Getting Started
- BL-19.4 API Usage Guide
- BL-19.3 Konfiguration/ENV
- BL-19.7 README-Integration

## „Weiterarbeit“-Default (wenn Nico sagt „mach weiter“)

Priorisierte Reihenfolge:

1. Offene `P0`-Items aus `docs/BACKLOG.md`
2. Dann aktive Prioritätsgates aus dem Job-Framework (aktuell: **BL-19 vor BL-20**)
3. Danach `P1` mit maximalem Produktnutzen bei minimalem Risiko
4. Doku und Betriebsrunbooks immer mitziehen (keine stillen Architekturänderungen)

## Definition of Done pro Iteration

Eine Iteration ist erst „done“, wenn:

- Code/Docs im Repo aktualisiert sind
- lokale Checks gelaufen sind (mind. `pytest`)
- kurzer Nachweis im Commit/Changelog vorhanden ist
- Push über `scripts/gpush` erfolgt ist

## Guardrails

- Keine Secrets in Repo/Logs/Docs
- Keine destruktiven Infra-Änderungen ohne expliziten Auftrag
- Bei unsicherem Scope zuerst Doku- oder Read-only-Hardening

### Blocker-Retry-Policy (verbindlich, externe/temporäre Fehler)

Für externe/temporäre Blocker (z. B. Endpoint-Timeouts, kurzfristige Infra-Unreachability) gilt:

1. **Nicht sofort dauerhaft blocken.**
2. **Grace Period: 3 Stunden** nach erstem Auftreten.
3. **Auto-Retry bis max. 3 Versuche** (inkl. Erstversuch), jeweils mit klarer Zeit + Fehlergrund im Issue-Kommentar.
4. Nach jedem Fehlversuch bleibt/kommt das Issue zurück auf **`status:todo`** für den nächsten Retry-Slot.
5. **Erst wenn alle 3 Versuche fehlschlagen:**
   - neues Follow-up-Issue anlegen (klarer externer Blocker, benötigter Input/Owner, Recheck-Kriterium),
   - ursprüngliches Issue auf `status:blocked` setzen und Follow-up verlinken.
