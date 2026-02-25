# Changelog

Alle bemerkenswerten Änderungen an diesem Projekt werden in diesem Dokument festgehalten.

Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).
Dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

---

## [Unreleased]

### Added
- Projektdokumentation: README.md, ARCHITECTURE.md, DEPLOYMENT_AWS.md, OPERATIONS.md
- Basis-Verzeichnisstruktur (`docs/`, `scripts/`, `.github/workflows/`)
- GitHub Actions Placeholder-Workflow für CI/CD

### Changed (2026-02-25 — Doku-Update: AWS-Naming, Tagging, Umgebungen)
- **DEPLOYMENT_AWS.md:** Neue Sektion „Tagging Standard" mit verbindlichen AWS-Tags (`Environment=dev`, `ManagedBy=openclaw`, `Owner=nico`, `Project=swisstopo`)
- **DEPLOYMENT_AWS.md:** Ist-Stand-Ressourcen (`swisstopo-dev-*`) als verifiziert eingetragen; ECS/ECR-Befehle auf korrekte Cluster-/Service-Namen aktualisiert
- **DEPLOYMENT_AWS.md:** Klarstellung: AWS-Naming `swisstopo` ist intern und intentional; keine Umbenennung nötig
- **DEPLOYMENT_AWS.md:** Explizit festgehalten: nur `dev`-Umgebung vorhanden; `staging` und `prod` noch nicht aufgebaut
- **ARCHITECTURE.md:** Swisstopo-Ressourcen korrekt als Ressourcen dieses Projekts (nicht Schwesterprojekt) eingetragen; Naming-Konvention und Umgebungs-Status ergänzt
- **README.md:** Hinweise zu AWS-Naming (`swisstopo`) und aktuellem Umgebungs-Stand (`dev` only) ergänzt
- **OPERATIONS.md:** Hinweise zu Umgebung (`dev` only) und AWS-Naming an prominenter Stelle ergänzt; Post-Release-Checkliste auf `dev`-Deployment angepasst

---

## [0.1.0] — 2026-02-25

### Added
- Initial Commit: Repository-Grundstruktur angelegt

[Unreleased]: https://github.com/nimeob/geo-ranking-ch/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/nimeob/geo-ranking-ch/releases/tag/v0.1.0
