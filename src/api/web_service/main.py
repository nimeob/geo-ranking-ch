"""Hauptmodul für die FastAPI-Anwendung."""

from fastapi import FastAPI, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .config import settings
from .routes import address, auth, async_jobs, compliance, ui
from .dependencies import limiter, rate_limit_exceeded_handler

# --- OpenAPI-Konfiguration ---
def custom_openapi():
    """Custom OpenAPI-Schema mit zusätzlichen Metadaten."""
    if settings.app:
        return get_openapi(
            title=settings.app_name,
            version=settings.app_version,
            description=(
                "API für geo-ranking-ch: Schweizer Geodaten, Adressen, Gebäudeinformationen, "
                "Höhenprofile und Compliance-Prüfungen. "
                "Nutzt Daten von swisstopo/GeoAdmin und dem Eidgenössischen Gebäude- und Wohnungsregister (GWR)."
            ),
            terms_of_service="https://geo-ranking.ch/terms",
            contact={
                "name": "geo-ranking-ch Support",
                "url": "https://github.com/nimeob/geo-ranking-ch",
                "email": "support@geo-ranking.ch",
            },
            license_info={
                "name": "MIT",
                "url": "https://opensource.org/licenses/MIT",
            },
            tags=[
                {"name": "address", "description": "Adressen, Geocoding und Standortinformationen"},
                {"name": "auth", "description": "Authentifizierung und Autorisierung"},
                {"name": "async_jobs", "description": "Asynchrone Jobs (Batch-Verarbeitung)"},
                {"name": "compliance", "description": "Compliance-Prüfungen und Korrekturen"},
                {"name": "ui", "description": "Frontend-Integration"},
            ],
            servers=[
                {"url": "http://localhost:8000", "description": "Lokale Entwicklung"},
                {"url": "https://api.geo-ranking.ch", "description": "Produktion"},
            ],
        )
    return get_openapi(title=settings.app_name, version=settings.app_version)

# --- API-Router ---
api_router = APIRouter(prefix=settings.api_prefix)

# Routen registrieren
api_router.include_router(address.router, tags=["address"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(async_jobs.router, tags=["async_jobs"])
api_router.include_router(compliance.router, tags=["compliance"])
api_router.include_router(ui.router, tags=["ui"])

# --- FastAPI-App ---
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    docs_url=settings.docs_url,
    openapi_url=settings.openapi_url,
    openapi_schema_extra={
        "info": {
            "x-logo": {
                "url": "https://geo-ranking.ch/logo.png",
                "altText": "geo-ranking-ch Logo",
            }
        }
    },
)

# Custom OpenAPI-Schema
app.openapi_schema = custom_openapi

# CORS-Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Router mounten
app.include_router(api_router)

# Health-Check-Endpoint
@app.get("/health", tags=["health"])
@limiter.limit("10/minute")
async def health_check(request: Request):
    """Health-Check-Endpoint für Monitoring."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "services": {
            "geo_admin": "healthy",
            "gwr": "healthy",
        },
    }