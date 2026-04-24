"""Dependencies für FastAPI (Auth, GeoUtils, Rate Limiting, etc.)."""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import APIKeyHeader
from typing import Annotated
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from .config import settings

# --- Rate Limiter ---
limiter = Limiter(key_func=get_remote_address)

# --- GeoUtils Dependency ---
class GeoUtils:
    """Wrapper für Geo-Utilities mit Caching."""
    def __init__(self):
        from ...geo_utils import (
            geocode_ch,
            elevation_at,
            wgs84_to_lv95,
            lv95_to_wgs84,
            location_info,
            building_info,
            haversine_km,
        )
        self.geocode_ch = geocode_ch
        self.elevation_at = elevation_at
        self.wgs84_to_lv95 = wgs84_to_lv95
        self.lv95_to_wgs84 = lv95_to_wgs84
        self.location_info = location_info
        self.building_info = building_info
        self.haversine_km = haversine_km

# Singleton-Instanz
geo_utils = GeoUtils()

def get_geo_utils() -> GeoUtils:
    """Stellt eine GeoUtils-Instanz bereit."""
    return geo_utils

# --- API-Key Auth ---
api_key_header = APIKeyHeader(name=settings.api_key_header, auto_error=False)

async def verify_api_key(api_key: Annotated[str | None, Depends(api_key_header)]) -> str:
    """Überprüft den API-Key."""
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API-Key fehlt. Bitte im Header 'X-API-Key' angeben.",
        )
    # Hier könnte eine Datenbankprüfung erfolgen
    # if not is_valid_api_key(api_key):
    #     raise HTTPException(status_code=403, detail="Ungültiger API-Key.")
    return api_key

# --- Rate Limiting ---
@limiter.limit("100/minute")
async def rate_limited(request: Request) -> None:
    """Rate Limiting für alle Endpoints."""
    pass

async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handler für Rate-Limit-Überschreitungen."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": "Zu viele Anfragen. Bitte versuchen Sie es später erneut.",
            "retry_after": exc.retry_after,
        },
    )