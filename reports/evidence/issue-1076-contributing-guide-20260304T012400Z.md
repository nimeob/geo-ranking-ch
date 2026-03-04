# Issue #1076 – CONTRIBUTING Kurzguide (Dev-Workflow)

## Änderungen
- CONTRIBUTING um direkte Lint/Format-Kommandos ergänzt (`ruff check .`, `ruff format .`)
- Neue Doku-Regression `tests/test_contributing_docs.py`:
  - prüft Setup/Dev-Start/Tests/Lint-Format-Marker
  - guardt gegen Deploy/Infra-Anleitungen im Dev-Guide

## Testnachweis
```bash
.venv-test/bin/python -m pytest -q tests/test_contributing_docs.py tests/test_markdown_links.py
```
Ergebnis: `3 passed`

## Acceptance Smoke (frischer Checkout-Flow, lokal)
```bash
PORT=18080 python3 -m src.api.web_service
curl -fsS http://127.0.0.1:18080/healthz
```
Ergebnis: `healthz-ok`
