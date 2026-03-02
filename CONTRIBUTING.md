# Contributing (Dev)

Dieser Guide ist **dev-only** und bewusst kurz.

**Out of scope:** Deployments, Staging/Prod, Promotion, AWS-Infrastruktur.

## Voraussetzungen

- Python **3.12**
- `git`

Optional (empfohlen): `pre-commit` Hooks für Format/Lint (siehe unten).

## Setup (frischer Checkout)

```bash
git clone https://github.com/nimeob/geo-ranking-ch.git
cd geo-ranking-ch

python3.12 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt -r requirements-dev.txt
```

## Lokaler Dev-Start

### API

```bash
python -m src.api.web_service
```

Default Healthcheck:

```bash
curl -sS http://localhost:8080/health
curl -sS http://localhost:8080/healthz  # dev-only (mit Build-Info)
```

### UI (separater Service)

```bash
python -m src.ui.service
```

Healthcheck:

```bash
curl -sS http://localhost:8080/healthz
```

> Hinweis: API und UI nutzen defaultmäßig denselben Port (`8080`). Starte sie daher nicht gleichzeitig ohne Port-Override (siehe README: `PORT`/`WEB_PORT`).

## Tests

```bash
pytest -q
# oder gezielt
pytest tests/ -v
```

Nützliche, reproduzierbare Checks:

```bash
./scripts/check_crawler_regression.sh
./scripts/check_docs_quality_gate.sh
./scripts/check_bl334_split_smokes.sh
```

## Lint / Format

Wir nutzen `pre-commit` (ruff + black).

```bash
pre-commit install
pre-commit run --all-files
```

## PR-Workflow (kurz)

- Branch erstellen
- Tests + `pre-commit` lokal laufen lassen
- PR öffnen (kleine, reviewbare Changes)

Siehe auch: `README.md` (Lokale Entwicklung) und Runbooks unter `docs/`.
