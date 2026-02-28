# Workstream-Balance Baseline

- Parent: #98
- Work-Package: #99
- Stand: 2026-02-28T07:05:00+00:00 (UTC)

## Reproduzierbare Ermittlung

```bash
# Markdown-Report (für Doku)
python3 scripts/github_repo_crawler.py --print-workstream-balance --format markdown

# JSON-Report (für Automatisierung/Weiterverarbeitung)
python3 scripts/github_repo_crawler.py --print-workstream-balance --format json
```

Methodik (aus `scripts/github_repo_crawler.py`):
- Grundlage sind offene Issues (`gh issue list --state open`)
- ausgeschlossen werden `status:blocked` und `crawler:auto`
- Workstream-Zuordnung erfolgt heuristisch über Keywords in Titel/Body
- TODO/FIXME-Findings werden nur als **actionable** gewertet; erledigte/historische Marker (`✅`, `erledigt`, `abgeschlossen`, `closed`, `changelog`) werden gefiltert. Reine Erwähnungen innerhalb von Überschriften/Freitext (z. B. `TODO-Filter`) lösen keine Finding-Issues aus.
- Ein offenes P0-Catch-up-Issue (`[Crawler][P0] Workstream-Balance ...`) wird automatisch geschlossen, sobald der Gap wieder im Zielkorridor (`<= 2`) liegt.
- Bei Catch-up-Bedarf wird zusätzlich ein **minimaler Delta-Plan** berechnet (`target_min_count` + `delta` pro Rückstands-Workstream), damit Worker direkt konkrete Folge-Issues ableiten können.

## Baseline-Werte

- Development: **1**
- Dokumentation: **1**
- Testing: **1**
- Gap (max-min): **0**
- Ziel-Gap: **<= 2**
- Catch-up nötig: **nein**

Hinweis (2026-02-27): Die aktuelle offene, nicht-blockierte Catch-up-Referenz (#261) wird heuristisch allen drei Workstreams zugeordnet; der Gap bleibt dennoch im Zielkorridor, daher ist kein zusätzlicher P0-Catch-up nötig.

## Catch-up-Empfehlung im Report/Issue-Body

Sobald `needs_catchup=true`, enthält die Ausgabe zusätzlich:

- `target_min_count`: Mindestziel pro Workstream auf Basis des aktuellen Maximums
- `categories[]`: nur Rückstands-Workstreams mit positivem Delta
- `delta`: minimale Anzahl zusätzlicher Catch-up-Issues, um den Zielkorridor wieder zu erreichen

Beispiel (Dev=6, Doku=6, Testing=3, Ziel-Gap<=2):

- Ziel-Mindeststand je Workstream: **4**
- Testing: **+1** (aktuell 3, Ziel >= 4)

## Catch-up-Plan (Ziel-Delta)

Zielwert bleibt verbindlich: **Gap <= 2** zwischen Development, Dokumentation und Testing.

Wenn der Gap künftig wieder >2 wird:
1. Rückstands-Workstream identifizieren (Report-Ausgabe als Referenz anhängen).
2. Sofort 1-2 atomare Catch-up-Issues für den Rückstand öffnen/freigeben.
3. Innerhalb der nächsten Iteration mindestens ein Catch-up-Issue abschließen.
4. Baseline-Report aktualisieren und Delta transparent nachführen.

## CI-/Smokepfad für Crawler-Regressionscheck (WP3)

```bash
# lokaler/CI-kompatibler Check-Command
./scripts/check_crawler_regression.sh
```

Der Command läuft im Migrationsmodus primär über OpenClaw (siehe `scripts/run_openclaw_migrated_job.py --job crawler-regression`).
Der GitHub-Workflow `.github/workflows/crawler-regression.yml` bleibt als manueller Fallback (`workflow_dispatch`) erhalten.

## Referenzen

- Crawler-Script: `scripts/github_repo_crawler.py`
- Crawler-Regression-Check: `scripts/check_crawler_regression.sh`
- OpenClaw-Runner: `scripts/run_openclaw_migrated_job.py`
- Manual-Fallback-Workflow: `.github/workflows/crawler-regression.yml`
- Parent-Issue: #98
- Recovery-Issue (auto-closed): #217
- Related Testing-WPs: #100, #101
