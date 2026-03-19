#!/usr/bin/env python3
"""Gemeinsame Helfer für Legacy-Kompatibilitäts-Wrapper unter ``src``.

Die Root-Module unter ``src`` bleiben als stabile Import-/Entrypoint-Brücken
bestehen, während die kanonischen Implementierungen in ``src.api``, ``src.ui``
odеr ``src.shared`` liegen. Dieses Modul bündelt die dünne Alias-/Proxy-Logik,
damit Wrapper konsistent bleiben und keine leicht driftenden Einzelvarianten
pflegen müssen.
"""

from __future__ import annotations

from importlib import import_module
import sys
import types
from typing import Any


def _is_forwardable_attribute(name: str) -> bool:
    return name not in {
        "__dict__",
        "__class__",
        "__spec__",
        "__loader__",
        "__package__",
        "__name__",
    }


class _ForwardingProxyModule(types.ModuleType):
    _forward_target: types.ModuleType

    def __getattr__(self, name: str) -> Any:  # pragma: no cover - thin compatibility proxy
        return getattr(self._forward_target, name)

    def __dir__(self) -> list[str]:  # pragma: no cover - thin compatibility proxy
        return sorted(set(super().__dir__()) | set(dir(self._forward_target)))

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        if _is_forwardable_attribute(name):
            setattr(self._forward_target, name, value)

    def __delattr__(self, name: str) -> None:
        super().__delattr__(name)
        if _is_forwardable_attribute(name) and hasattr(self._forward_target, name):
            delattr(self._forward_target, name)


def install_module_alias(current_name: str, target_name: str):
    """Replace the current module entry with the canonical target module."""
    target_module = import_module(target_name)
    sys.modules[current_name] = target_module
    return target_module


def install_forwarding_proxy(
    current_name: str,
    module_globals: dict[str, Any],
    target_name: str,
):
    """Install a mutation-forwarding proxy for legacy wrappers.

    This keeps existing references to the legacy module object working while
    mirroring attribute writes/deletes to the canonical module.
    """
    target_module = import_module(target_name)
    current_module = sys.modules[current_name]

    module_globals.update(
        {
            key: value
            for key, value in vars(target_module).items()
            if key not in {"__name__", "__package__"}
        }
    )

    current_module.__class__ = _ForwardingProxyModule
    current_module._forward_target = target_module
    return target_module
