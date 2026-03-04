# Issue #1074 – Error-Envelope Harmonisierung (Evidence)

## Scope
- Validation-Fehler explizit als `400 bad_request` mit `details[]` über zentrale Helper (`_send_error`) auch für GET-Validierungsrouten.
- NotFound bleibt `404 not_found`.
- Generische Laufzeitfehler bleiben `500 internal`.

## Änderungen
- `src/api/web_service.py`
  - GET-Validierungspfade (`/analyze/history`, `/analyze/jobs/{id}/notifications`, `/analyze/jobs/{id}`, `/analyze/results/{id}`) nutzen jetzt konsistent `_send_error(..., error="bad_request", details=[...])` statt ad-hoc `_send_json`.
- `tests/test_web_service_request_validation.py`
  - Neue Regressionen:
    - invalides `view` bei `/analyze/results/{id}` -> `400 bad_request` mit Details.
    - unbekannte Result-Ressource -> `404 not_found`.
- `docs/api/async-v1.md`
  - Fehler-Envelope präzisiert: `details[]` bei `bad_request` ist für Body- und Query/Header-Validierung konsistent.

## Testnachweis
```bash
.venv-test/bin/python -m pytest -q \
  tests/test_web_service_request_validation.py \
  tests/test_web_service_request_logging.py \
  tests/test_user_docs.py \
  tests/test_markdown_links.py
```

Ergebnis: `24 passed`
