"""API-Routen für die UI-Integration (Frontend-Bridge)."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional
from pathlib import Path
from ..dependencies import verify_api_key, limiter
from ..config import settings

router = APIRouter(prefix="/ui")

# --- Statische Dateien und Templates ---
# Pfad zu den UI-Dateien
UI_STATIC_PATH = Path(__file__).parent.parent.parent.parent / "ui" / "static"
UI_TEMPLATES_PATH = Path(__file__).parent.parent.parent.parent / "ui" / "templates"

# Statische Dateien mounten (für JS/CSS)
if UI_STATIC_PATH.exists():
    router.mount("/static", StaticFiles(directory=UI_STATIC_PATH), name="static")

# Templates für Server-side Rendering (falls benötigt)
templates = Jinja2Templates(directory=UI_TEMPLATES_PATH)

# --- Routen ---
@router.get(
    "/",
    response_class=HTMLResponse,
    summary="UI-Hauptseite",
    description="Lädt die Hauptseite der Web-UI.",
)
async def get_ui_index(request: Request):
    """Lädt die UI-Hauptseite."""
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception:
        # Fallback: Einfache HTML-Seite mit Link zur API-Dokumentation
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
                <head>
                    <title>geo-ranking-ch UI</title>
                    <meta charset="utf-8">
                </head>
                <body>
                    <h1>Willkommen bei geo-ranking-ch</h1>
                    <p><a href="/docs">API-Dokumentation</a></p>
                    <p><a href="/ui/map">Karte anzeigen</a></p>
                </body>
            </html>
            """
        )

@router.get(
    "/map",
    response_class=HTMLResponse,
    summary="Interaktive Karte",
    description="Lädt eine interaktive Karte für Geodaten.",
)
async def get_ui_map(request: Request):
    """Lädt die interaktive Karte."""
    try:
        return templates.TemplateResponse("map.html", {"request": request})
    except Exception:
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
                <head>
                    <title>Karte - geo-ranking-ch</title>
                    <meta charset="utf-8">
                    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
                    <style>
                        #map { height: 100vh; }
                    </style>
                </head>
                <body>
                    <div id="map"></div>
                    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
                    <script>
                        const map = L.map('map').setView([46.8, 8.3], 8);
                        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                            attribution: '© OpenStreetMap'
                        }).addTo(map);
                        L.marker([46.8, 8.3]).addTo(map)
                            .bindPopup('Beispielstandort')
                            .openPopup();
                    </script>
                </body>
            </html>
            """
        )

@router.get(
    "/api-proxy/{path:path}",
    summary="API-Proxy für die UI",
    description=(
        "Leitet Anfragen von der UI an die Backend-API weiter. "
        "Wird verwendet, um CORS-Probleme zu vermeiden."
    ),
    responses={200: {"description": "API-Response"}},
)
@limiter.limit("100/minute")
async def api_proxy(
    request: Request,
    path: str,
    api_key: str = Depends(verify_api_key),
):
    """Leitet Anfragen an die Backend-API weiter."""
    try:
        # Hier könnte die Anfrage an die interne API weitergeleitet werden
        # Beispiel: 
        # import httpx
        # async with httpx.AsyncClient() as client:
        #     response = await client.request(
        #         method=request.method,
        #         url=f"http://localhost:8000/{path}",
        #         headers=request.headers,
        #     )
        # return JSONResponse(content=response.json(), status_code=response.status_code)
        return JSONResponse(
            content={"error": "Proxy nicht implementiert"},
            status_code=501,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Proxy-Anfrage fehlgeschlagen: {str(e)}",
        )