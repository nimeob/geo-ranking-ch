#!/usr/bin/env python3
"""Kompatibilitäts-Wrapper für ``src.shared.gui_mvp``.

Die kanonische GUI-MVP-Implementierung liegt im Shared-Source-Bereich unter
``src/shared/gui_mvp.py``. Dieser Wrapper hält Legacy-Importpfade stabil.
"""

from importlib import import_module
import sys

_shared_module = import_module("src.shared.gui_mvp")
sys.modules[__name__] = _shared_module
