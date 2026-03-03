# Issue #947 Evidence — GUI Auth UX E2E + Cookie Security

- Timestamp (UTC): 2026-03-03T17:12:09Z
- Scope: Login/Redirect/Logout-E2E-Nachweis sowie Cookie-Attribute (HttpOnly, SameSite, Secure) für den GUI-BFF-Auth-Flow.

## 1) E2E-Flow (Guard + Redirect + Logout)

Command:

```bash
python3 -m unittest tests.test_web_service_bff_gui_guard
```

Exit code: 0

Output:

```text
/home/linuxbrew/.linuxbrew/Cellar/python@3.14/3.14.3_1/lib/python3.14/tempfile.py:484: ResourceWarning: Implicitly cleaning up <HTTPError 302: 'Found'>
  _warnings.warn(self.warn_message, ResourceWarning)
...
----------------------------------------------------------------------
Ran 3 tests in 0.239s

OK
<sys>:0: ResourceWarning: unclosed file <_io.TextIOWrapper name=5 encoding='utf-8'>
<sys>:0: ResourceWarning: unclosed file <_io.TextIOWrapper name=3 encoding='utf-8'>
```

## 2) Cookie Security Attribute Regression

Command:

```bash
pytest -q tests/test_bff_session.py -k "contains_httponly or contains_samesite_lax or secure_flag_when_enabled or no_secure_flag_when_disabled"
```

Exit code: 0

Output:

```text
.....                                                                    [100%]
5 passed, 40 deselected in 0.03s
```

## 3) Dokumentations-Regression

Command:

```bash
pytest -q tests/test_gui_auth_bff_session_flow_docs.py tests/test_markdown_links.py
```

Exit code: 0

Output:

```text
...                                                                      [100%]
3 passed in 0.12s
```

## Ergebnis

- E2E-Guard-Pfad (redirects + logout) ist grün.
- Cookie-Attribute sind über Unit-Tests abgesichert.
- Doku-Link-Integrität ist grün.
