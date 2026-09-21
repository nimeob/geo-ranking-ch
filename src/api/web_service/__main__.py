#!/usr/bin/env python3
"""Module entrypoint for ``python -m src.api.web_service``."""
from src.api import web_service as _web_service

if __name__ == "__main__":
    main = getattr(_web_service, "main", None)
    if main is None:
        raise AttributeError("main entrypoint not found in src.api.web_service")
    main()
