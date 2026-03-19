#!/usr/bin/env python3
"""Kompatibilitäts-Wrapper für ``src.shared.gui_mvp``.

Die kanonische GUI-MVP-Implementierung liegt im Shared-Source-Bereich unter
``src/shared/gui_mvp.py``. Dieser Wrapper hält Legacy-Importpfade stabil.
"""

from src._legacy_module_proxy import install_module_alias

_shared_module = install_module_alias(__name__, "src.shared.gui_mvp")
