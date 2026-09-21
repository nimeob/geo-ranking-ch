"""Compatibility bridge for ``python -m src.api.web_service``.

The canonical implementation lives in ``src/api/web_service.py`` (module).
This package keeps the module path addressable as a package so the
``__main__`` entrypoint works while imports such as
``from src.api.web_service import Handler`` continue to resolve against the
canonical module.
"""

from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

from src._legacy_module_proxy import install_forwarding_proxy

_LEGACY_MODULE_NAME = "src.api._web_service_legacy_impl"


def _ensure_legacy_module_loaded() -> str:
    existing = sys.modules.get(_LEGACY_MODULE_NAME)
    if isinstance(existing, ModuleType):
        return _LEGACY_MODULE_NAME
    legacy_path = Path(__file__).resolve().parents[1] / "web_service.py"
    spec = spec_from_file_location(_LEGACY_MODULE_NAME, legacy_path)
    if spec is None or spec.loader is None:
        raise ImportError(
            f"Unable to load legacy web_service module from {legacy_path}"
        )
    module = module_from_spec(spec)
    sys.modules[_LEGACY_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return _LEGACY_MODULE_NAME


_target_name = _ensure_legacy_module_loaded()
install_forwarding_proxy(__name__, globals(), _target_name)
