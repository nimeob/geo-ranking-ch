"""Web Service Module für geo-ranking-ch.

Enthält:
- FastAPI/Flask-App-Initialisierung
- API-Routen (nach Domänen getrennt)
- Modelle, Dependencies und Utilities
"""

from .main import app
from .routes import address, auth, async_jobs, compliance, ui
from .models import AddressRequest, AddressResponse, JobStatus
from .config import settings

__all__ = [
    "app",
    "settings",
    "AddressRequest",
    "AddressResponse",
    "JobStatus",
]