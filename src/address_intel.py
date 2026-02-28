#!/usr/bin/env python3
"""Kompatibilitäts-Wrapper für ``src.api.address_intel``.

Die kanonische Implementierung wurde in den API-Source-Bereich migriert.
Der Wrapper hält den Legacy-Importpfad unter ``src`` kompatibel.
"""

from importlib import import_module
import sys
import types

_api_module = import_module("src.api.address_intel")


def _is_forwardable(name: str) -> bool:
    return name not in {"__dict__", "__class__", "__spec__", "__loader__", "__package__", "__name__"}


class _ProxyModule(types.ModuleType):
    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if _is_forwardable(name):
            setattr(_api_module, name, value)

    def __delattr__(self, name):
        super().__delattr__(name)
        if _is_forwardable(name) and hasattr(_api_module, name):
            delattr(_api_module, name)


globals().update({k: v for k, v in vars(_api_module).items() if k not in {"__name__", "__package__"}})
sys.modules[__name__].__class__ = _ProxyModule


def __getattr__(name):  # pragma: no cover - thin compatibility proxy
    return getattr(_api_module, name)


def __dir__():  # pragma: no cover - thin compatibility proxy
    return sorted(set(globals()) | set(dir(_api_module)))
