#!/usr/bin/env python3
"""Kompatibilitäts-Wrapper für ``src.api.personalized_scoring``.

Die kanonische Implementierung wurde in den API-Source-Bereich migriert.
Der Wrapper hält den Legacy-Importpfad unter ``src`` kompatibel.
"""

from importlib import import_module
import sys

_api_module = import_module("src.api.personalized_scoring")
sys.modules[__name__] = _api_module
