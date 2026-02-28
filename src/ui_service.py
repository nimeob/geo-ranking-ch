#!/usr/bin/env python3
"""Kompatibilitäts-Wrapper für ``src.ui.service``.

Die kanonische UI-Service-Implementierung wurde nach ``src/ui/service.py``
verschoben. Dieser Wrapper hält bestehende Entrypoints stabil
(``python -m src.ui_service``).
"""

from importlib import import_module
import sys

_ui_module = import_module("src.ui.service")
sys.modules[__name__] = _ui_module

if __name__ == "__main__":
    _ui_module.main()
