# Issue #995 Verification Run

- Timestamp (UTC): 20260303T185411Z
- Runtime: .venv
- Command:
```bash
./.venv/bin/python -m pytest -q tests/test_bff_session.py tests/test_bff_oidc.py tests/test_bff_portal_proxy.py tests/test_bff_integration.py tests/test_web_service_bff_gui_guard.py tests/test_history_navigation_integration.py tests/test_history_pagination_and_guards.py tests/test_gui_auth_bff_session_flow_docs.py tests/test_markdown_links.py
```

## Output
```text
........................................................................ [ 34%]
........................................................................ [ 68%]
.................................................................        [100%]
209 passed in 1.22s
```

- Exit code: 0

## Post-link-sync rerun

- Command:
```bash
./.venv/bin/python -m pytest -q tests/test_gui_auth_bff_session_flow_docs.py tests/test_markdown_links.py
```

```text
....                                                                     [100%]
4 passed in 0.13s
```

- Exit code: 0
