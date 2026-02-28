#!/usr/bin/env python3
"""Kompatibilitäts-Wrapper für ``src.ui.gui_mvp``.

Die kanonische GUI-MVP-Implementierung liegt im UI-Source-Bereich unter
``src/ui/gui_mvp.py``. Dieser Wrapper hält Legacy-Importpfade stabil.
"""

from importlib import import_module
import sys

_ui_module = import_module("src.ui.gui_mvp")
sys.modules[__name__] = _ui_module
