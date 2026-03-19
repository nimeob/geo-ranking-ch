#!/usr/bin/env python3
"""Kompatibilitäts-Wrapper für ``src.api.suitability_light``.

Die kanonische Implementierung wurde in den API-Source-Bereich migriert.
Der Wrapper hält den Legacy-Importpfad unter ``src`` kompatibel.
"""

from src._legacy_module_proxy import install_module_alias

_api_module = install_module_alias(__name__, "src.api.suitability_light")
