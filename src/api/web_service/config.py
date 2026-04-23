"""Konfiguration für den Web-Service (Environment Variables, Settings)."""

from pydantic_settings import BaseSettings
from pydantic import Field, HttpUrl
from typing import Optional

class Settings(BaseSettings):
    """Einstellungen für den Web-Service."""

    # App
    app_name: str = "geo-ranking-ch API"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="APP_DEBUG")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # API
    api_prefix: str = "/api/v1"
    docs_url: str = "/docs"
    openapi_url: str = "/openapi.json"

    # GeoAdmin API
    geo_admin_base_url: HttpUrl = Field(
        default="https://api3.geo.admin.ch/rest/services",
        env="GEO_ADMIN_BASE_URL"
    )
    geo_admin_timeout: int = 10

    # Caching
    cache_ttl_seconds: int = 3600  # 1 Stunde
    cache_max_size: int = 1000

    # Auth
    api_key_header: str = "X-API-Key"
    oidc_issuer: Optional[HttpUrl] = Field(default=None, env="OIDC_ISSUER")
    oidc_audience: str = Field(default="geo-ranking-ch", env="OIDC_AUDIENCE")

    # Datenbank (optional)
    db_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Globale Instanz
settings = Settings()