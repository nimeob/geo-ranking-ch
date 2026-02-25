# Operations — geo-ranking-ch

Arbeitsmodus, Branching-Strategie, Commit-Regeln und Release-Checkliste.

> **Umgebungen:** Aktuell existiert ausschließlich eine **`dev`-Umgebung** auf AWS. `staging` und `prod` sind noch nicht aufgebaut. Alle Deploy-Schritte in dieser Dokumentation beziehen sich auf `dev`, sofern nicht anders angegeben.

> **AWS-Naming:** AWS-Ressourcen heißen intern `swisstopo` (z. B. Cluster `swisstopo-dev`). Das ist so gewollt — der Repo-Name `geo-ranking-ch` und das interne AWS-Naming divergieren bewusst.

---

## Branching-Strategie

Dieses Projekt verwendet **Trunk-Based Development** mit kurzlebigen Feature-Branches.

```
main          ──●──●──●──●──●──▶  (immer deploybar)
                 ↑  ↑
feature/xyz ──●──┘  │
fix/abc     ──●──●──┘
```

| Branch-Typ | Namensschema | Lebensdauer |
|---|---|---|
| Feature | `feature/<kurze-beschreibung>` | bis Merge, max. 3 Tage |
| Bugfix | `fix/<kurze-beschreibung>` | bis Merge |
| Hotfix | `hotfix/<issue-id>` | sofort mergen |
| Release | `release/v<x.y.z>` | bis Tag + Merge, dann löschen |

**Regeln:**
- `main` ist immer deploybar
- Keine direkten Commits auf `main` (außer kleinen Doku-Änderungen)
- Feature-Branches werden via Pull Request gemergt
- Branches nach dem Merge löschen

---

## Commit-Konventionen

Dieses Projekt folgt [Conventional Commits](https://www.conventionalcommits.org/).

### Format

```
<typ>(<scope>): <beschreibung>

[optionaler body]

[optionaler footer: BREAKING CHANGE / Closes #issue]
```

### Typen

| Typ | Bedeutung |
|---|---|
| `feat` | Neue Funktionalität |
| `fix` | Bugfix |
| `docs` | Nur Doku-Änderungen |
| `style` | Formatierung, kein Logik-Einfluss |
| `refactor` | Refactoring ohne Funktionsänderung |
| `test` | Tests hinzufügen oder korrigieren |
| `chore` | Build, Dependencies, CI, Konfiguration |
| `perf` | Performance-Verbesserung |
| `ci` | CI/CD-Konfiguration |
| `infra` | Infrastruktur / IaC |

### Beispiele

```bash
feat(ranking): add municipality score calculation
fix(ingest): handle missing coordinates in BFS data
docs(deployment): update AWS runbook with ECS details
chore(deps): upgrade boto3 to 1.35.0
infra(ecs): add Fargate task definition for api service
```

---

## Pull-Request-Regeln

### Checkliste vor dem Öffnen eines PRs

- [ ] Branch ist aktuell mit `main` (`git rebase main` oder `git merge main`)
- [ ] Alle Tests lokal grün
- [ ] Keine Secrets / Credentials im Code
- [ ] Commit-Messages folgen Conventional Commits
- [ ] `CHANGELOG.md` aktualisiert (bei Features/Bugfixes)
- [ ] Doku aktualisiert (falls API oder Architektur sich ändert)

### PR-Beschreibung

```markdown
## Was ändert sich?
<kurze Beschreibung>

## Warum?
<Motivation / verknüpftes Issue>

## Wie testen?
<Schritte zum Testen>

## Checkliste
- [ ] Tests
- [ ] Docs
- [ ] Kein Breaking Change / Breaking Change dokumentiert
```

### Review

- Mindestens **1 Approval** vor dem Merge
- CI muss grün sein
- Squash-Merge bevorzugt für saubere `main`-History

---

## Release-Prozess

### Semantic Versioning

Das Projekt folgt [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`

| Änderung | Version |
|---|---|
| Breaking Changes | MAJOR |
| Neue Funktionen (rückwärtskompatibel) | MINOR |
| Bugfixes | PATCH |

### Release-Checkliste

```bash
# 1. Release-Branch erstellen
git checkout -b release/v<x.y.z>

# 2. Version bumpen (falls vorhanden)
# vim pyproject.toml / package.json / version.py

# 3. CHANGELOG.md aktualisieren
#    - Abschnitt für neue Version anlegen
#    - Datum eintragen
#    - Änderungen aus Commits zusammenfassen

# 4. Commit
git commit -am "chore(release): prepare v<x.y.z>"

# 5. PR auf main öffnen und mergen

# 6. Tag setzen
git checkout main && git pull
git tag -a v<x.y.z> -m "Release v<x.y.z>"
git push origin v<x.y.z>

# 7. GitHub Release erstellen (optional)
#    → GitHub UI: Releases → Draft new release → Tag auswählen
```

### Post-Release

- [ ] Deployment in `dev` ausgelöst (via Tag-triggered CI oder manuell)
- [ ] Smoke-Test in `dev` durchgeführt
- [ ] _(prod/staging: noch nicht vorhanden — entfällt aktuell)_
- [ ] Release-Branch gelöscht
- [ ] Team informiert (falls relevant)

---

## Lokale Entwicklung

### Setup

```bash
git clone https://github.com/nimeob/geo-ranking-ch.git
cd geo-ranking-ch

# Virtuelle Umgebung (Python-Beispiel — Stack zu verifizieren)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# Pre-Commit Hooks installieren (TODO: .pre-commit-config.yaml anlegen)
# pre-commit install
```

### Empfohlene Tools

| Tool | Zweck | Pflicht |
|---|---|---|
| `pre-commit` | Linting/Formatierung vor Commit | empfohlen |
| `black` / `ruff` | Python-Formatierung | empfohlen |
| `pytest` | Tests | ja |
| `docker` | Lokale Container-Tests | empfohlen |
| `aws-vault` | Sichere AWS-Credential-Verwaltung | empfohlen |

---

## Incident-Prozess

1. **Erkennen:** Monitoring-Alarm oder User-Report
2. **Triagieren:** Schweregrad bestimmen (P1-P4)
3. **Mitigieren:** Rollback oder Hotfix
4. **Kommunizieren:** Status-Update (intern)
5. **Postmortem:** Ursache dokumentieren, Maßnahmen ableiten

Rollback-Prozedur: siehe [`DEPLOYMENT_AWS.md`](DEPLOYMENT_AWS.md#4-rollback-prozedur)
