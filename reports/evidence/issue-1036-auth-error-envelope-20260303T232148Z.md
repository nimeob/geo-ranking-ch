# Issue #1036 — Einheitliche 401/403 Auth-Error-Envelope (Evidence)

- Timestamp (UTC): 20260303T232148Z
- Branch: `worker-a/issue-1036-auth-error-envelope`

## Umsetzung

1. **Stabiles Auth-Error-Schema in BFF-Proxy-Guards** (`src/api/bff_portal_proxy.py`)
   - 401/403 liefern konsistent:
     - `ok: false`
     - `code: unauthorized|forbidden` (stabil)
     - `error` (detailierter Grund, z. B. `no_session_cookie`, `csrf_check_failed`)
     - `auth_reason` (falls Detailgrund von `code` abweicht)
     - `message`
     - `request_id`

2. **/auth/me harmonisiert** (`src/api/web_service.py`)
   - bei 401 bleibt `error` detailiert (z. B. `session_not_found`)
   - `code` ist stabil auf `unauthorized`
   - `auth_reason` + `request_id` sind vorhanden

3. **Error-Normalisierung robust gemacht** (`_normalize_error_payload`)
   - explizites `error` bleibt erhalten
   - `code` bleibt stabil referenzierbar

4. **Dev-Doku ergänzt** (`docs/BFF_FLOW.md`)
   - kurzer Abschnitt „Auth-Error Envelope (Dev-Stabilität, ab #1036)"

## Testnachweise

```bash
pytest -q tests/test_bff_portal_proxy.py tests/test_web_service_bff_gui_guard.py
pytest -q tests/test_web_service_request_validation.py tests/test_web_service_debug_trace_api.py tests/test_web_e2e.py
pytest -q tests/test_markdown_links.py tests/test_user_docs.py
```

Ergebnis:
- `63 passed`
- `77 passed, 52 subtests passed`
- `9 passed`
