#!/usr/bin/env python3
"""Kompatibilitäts-Wrapper für ``src.ui.service``.

Die kanonische UI-Service-Implementierung wurde nach ``src/ui/service.py``
verschoben. Dieser Wrapper hält bestehende Entrypoints stabil
(``python -m src.ui_service``).
"""

from src._legacy_module_proxy import install_module_alias

_ui_module = install_module_alias(__name__, "src.ui.service")

if __name__ == "__main__":
    _ui_module.main()
