# Workstream-Balance Baseline

- Parent: #98
- Work-Package: #99
- Stand: 2026-02-26T22:26:00+00:00 (UTC)

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

## Baseline-Werte

- Development: **4**
- Dokumentation: **4**
- Testing: **4**
- Gap (max-min): **0**
- Ziel-Gap: **<= 2**
- Catch-up nötig: **nein**

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

Der Command wird in GitHub Actions über den Workflow
`.github/workflows/crawler-regression.yml` ausgeführt.

## Referenzen

- Crawler-Script: `scripts/github_repo_crawler.py`
- Crawler-Regression-Check: `scripts/check_crawler_regression.sh`
- CI-Workflow: `.github/workflows/crawler-regression.yml`
- Parent-Issue: #98
- Related Testing-WPs: #100, #101
