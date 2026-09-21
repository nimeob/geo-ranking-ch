#!/usr/bin/env python3
"""Module entrypoint for ``python -m src.api.web_service``."""
from src.api import web_service as _legacy_impl

if __name__ == "__main__":
    _legacy_impl.main()
