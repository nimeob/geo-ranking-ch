#!/usr/bin/env python3
"""Kompatibilitäts-Wrapper für den API-Entrypoint unter ``src.api``.

Die kanonische Implementierung liegt in ``src/api/web_service.py``.
Dieser Wrapper hält bestehende Aufrufe (``python -m src.web_service`` und
``from src.web_service import ...``) stabil, während der API-Code in den
separaten Source-Bereich migriert wurde.
"""

from importlib import import_module
import sys

_api_module = import_module("src.api.web_service")
sys.modules[__name__] = _api_module

if __name__ == "__main__":
    _api_module.main()
