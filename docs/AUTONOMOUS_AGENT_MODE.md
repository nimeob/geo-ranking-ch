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

## „Weiterarbeit“-Default (wenn Nico sagt „mach weiter“)

Priorisierte Reihenfolge:

1. Offene `P0`-Items aus `docs/BACKLOG.md`
2. Danach `P1` mit maximalem Risikoabbau bei minimalem Eingriff
3. Doku und Betriebsrunbooks immer mitziehen (keine stillen Architekturänderungen)

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
