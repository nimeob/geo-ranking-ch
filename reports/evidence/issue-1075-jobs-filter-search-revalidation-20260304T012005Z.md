# Issue #1075 – /jobs Filter+Suche Revalidation (Duplicate Closeout)

## Summary
Die Anforderungen aus #1075 sind bereits in `main` umgesetzt (#768 + #971):
- Status-Filter in `/jobs`
- Job-ID-Suche
- URL-sharebare Query-Parameter (`jobs_status`, `jobs_q`) inkl. Legacy-Link-Kompatibilität

## Revalidation
```bash
.venv-test/bin/python -m pytest -q tests/test_ui_service.py tests/test_markdown_links.py
```

Ergebnis: `13 passed`

## Referenzen
- Implementierung: `src/ui/service.py`
- Regressionen: `tests/test_ui_service.py`
- Doku: `docs/gui/GUI_MVP_STATE_FLOW.md`
