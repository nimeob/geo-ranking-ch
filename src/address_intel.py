#!/usr/bin/env python3
"""Kompatibilitäts-Wrapper für ``src.api.address_intel``.

Die kanonische Implementierung wurde in den API-Source-Bereich migriert.
Der Wrapper hält den Legacy-Importpfad unter ``src`` kompatibel.
"""

from src._legacy_module_proxy import install_forwarding_proxy

_api_module = install_forwarding_proxy(__name__, globals(), "src.api.address_intel")
