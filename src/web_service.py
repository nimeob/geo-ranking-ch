#!/usr/bin/env python3
"""Kompatibilitäts-Wrapper für den API-Entrypoint unter ``src.api``.

Die kanonische Implementierung liegt in ``src/api/web_service.py``.
Dieser Wrapper hält bestehende Aufrufe (``python -m src.web_service`` und
``from src.web_service import ...``) stabil, während der API-Code in den
separaten Source-Bereich migriert wurde.
"""

from src._legacy_module_proxy import install_module_alias

_api_module = install_module_alias(__name__, "src.api.web_service")

if __name__ == "__main__":
    _api_module.main()
