# Issue #995 Verification Run

- Timestamp (UTC): 20260303T185228Z
- Runtime: .venv
- Command:
```bash
./.venv/bin/python -m pytest -q tests/test_bff_session.py tests/test_bff_oidc.py tests/test_bff_portal_proxy.py tests/test_bff_integration.py tests/test_web_service_bff_gui_guard.py tests/test_history_navigation_integration.py tests/test_history_pagination_and_guards.py tests/test_gui_auth_bff_session_flow_docs.py tests/test_markdown_links.py
```

## Output
```text
........................................................................ [ 34%]
........................................................................ [ 69%]
................................................................         [100%]
208 passed in 1.17s
```

- Exit code: 0
