# Contributing (Dev)

Dieser Guide ist **dev-only** und bewusst kurz.

**Out of scope:** Deployments, Staging/Prod, Promotion, AWS-Infrastruktur.

## Voraussetzungen

- Python **3.12**
- `git`

Optional (empfohlen): `pre-commit` Hooks für Format/Lint.

## Setup (frischer Checkout)

```bash
git clone https://github.com/nimeob/geo-ranking-ch.git
cd geo-ranking-ch

python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
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

> Hinweis: API und UI nutzen standardmäßig denselben Port (`8080`).
> Entweder einzeln starten **oder** einen Port-Override setzen (siehe `README.md`, `PORT`/`WEB_PORT`).

## Tests

```bash
# schneller Basislauf
pytest -q

# optional gezielter Lauf
pytest tests/ -v
```

Nützliche reproduzierbare Checks:

```bash
./scripts/check_crawler_regression.sh
./scripts/check_docs_quality_gate.sh
make dev-smoke  # Standard-Entry-Point (delegiert auf scripts/check_bl334_split_smokes.sh)
npm run dev:smoke  # DX-Bundle: Lint + Typecheck + Smoke-Subset
make dev-check  # Pre-PR-Entry-Point (Lint + Type/Syntax + Unit-Tests)
```

## Lint / Format

Wir nutzen `pre-commit` (ruff + black):

```bash
pre-commit install
pre-commit run --all-files
```

Optional direkt (ohne Hook):

```bash
ruff check .
ruff format .
```

## Akzeptanz (frischer Checkout, minimal)

Wenn folgende Kommandos lokal funktionieren, ist der Guide im Soll:

```bash
python -m src.api.web_service
# in zweiter Shell:
curl -sS http://localhost:8080/healthz
pytest -q
```

## Vor PR ausführen

```bash
make dev-check
```

Der Target läuft fail-closed und bündelt:

1. `pre-commit run`
2. `python -m compileall -q src tests scripts`
3. `pytest -q`

Optional:

```bash
# Voller Lint-Lauf über alle Dateien
LINT_SCOPE=all make dev-check

# Eingeschränkter Unit-Scope für schnelle Iteration
UNIT_TEST_TARGETS="tests/test_user_docs.py tests/test_markdown_links.py" make dev-check
```

## PR-Workflow (kurz)

- Branch erstellen
- `make dev-check` lokal laufen lassen
- PR öffnen (kleine, reviewbare Changes)

Siehe auch: `README.md` (Lokale Entwicklung) und Runbooks unter `docs/`.
