"""API-Routen für Adressen und Geodaten."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Optional, List
from ..dependencies import get_geo_utils, verify_api_key, limiter
from ..models.address import AddressRequest, AddressResponse, LocationInfoResponse
from ..config import settings
from fastapi import Request

router = APIRouter()

# --- Modelle mit Beispielen ---
class GeocodeRequest(BaseModel):
    """Request-Modell für Geocoding."""
    query: str = Field(
        ...,
        description="Suchbegriff (Adresse, Ortsname, Gipfel, etc.)",
        example="Espenmoosstrasse 18, 9008 St. Gallen",
    )
    origins: str = Field(
        default="address,gg25,gazetteer",
        description="Kommagetrennte Quellen: address (Adressen), gg25 (Gemeinden), gazetteer (POIs)",
        example="address,gg25",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximale Anzahl Ergebnisse",
        example=5,
    )

class ElevationRequest(BaseModel):
    """Request-Modell für Höhenabfrage."""
    lat: float = Field(
        ...,
        description="Breitengrad (WGS84)",
        example=47.3769,
    )
    lon: float = Field(
        ...,
        description="Längengrad (WGS84)",
        example=8.5417,
    )

# --- Routen mit OpenAPI-Metadaten ---
@router.get(
    "/geocode",
    response_model=List[AddressResponse],
    summary="Adresse oder Ort in der Schweiz suchen",
    description=(
        "Durchsucht das Schweizer Adressregister (GWR) und GeoAdmin-Daten. "
        "Unterstützt Adressen, Gemeinden, Kantone, Berge, Seen und ÖV-Haltestellen. "
        "Die Ergebnisse enthalten Koordinaten in WGS84 und LV95."
    ),
    response_description="Liste von Adressen/Orten mit Koordinaten und Metadaten",
    responses={
        200: {
            "description": "Erfolgreiche Suche",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "label": "Espenmoosstrasse 18, 9008 St. Gallen",
                            "lat": 47.4234,
                            "lon": 9.3769,
                            "easting": 2745000.0,
                            "northing": 1270000.0,
                            "origin": "address",
                            "zip_code": "9008",
                            "city": "St. Gallen",
                            "egid": "CH123456789",
                            "feature_id": "12345",
                        }
                    ]
                }
            },
        },
        400: {"description": "Ungültige Anfrage (z. B. leere Suchanfrage)"},
        500: {"description": "Serverfehler (z. B. GeoAdmin-API nicht erreichbar)"},
    },
)
@limiter.limit("100/minute")
async def geocode(
    request: Request,
    query: str = Query(..., description="Suchbegriff (Adresse, Ortsname, etc.)"),
    origins: str = Query(
        default="address,gg25,gazetteer",
        description="Kommagetrennte Quellen: address, gg25, gazetteer, parcel",
    ),
    limit: int = Query(default=5, ge=1, le=20),
    geo_utils=Depends(get_geo_utils),
    api_key: str = Depends(verify_api_key),
) -> List[AddressResponse]:
    """Geocoding für Schweizer Adressen/Orte."""
    try:
        results = geo_utils.geocode_ch(query, origins=origins, limit=limit)
        return [AddressResponse(**r) for r in results]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Geocoding fehlgeschlagen: {str(e)}",
        )

@router.get(
    "/elevation",
    response_model=float,
    summary="Höhe über Meer für eine Koordinate abrufen",
    description=(
        "Gibt die Höhe in Metern über Meer für einen WGS84-Punkt zurück. "
        "Nutzt Daten von swisstopo (DHM25/SRTM). "
        "Funktioniert nur für Koordinaten in der Schweiz und Liechtenstein."
    ),
    response_description="Höhe in Metern über Meer",
    responses={
        200: {
            "description": "Erfolgreiche Höhenabfrage",
            "content": {
                "application/json": {
                    "example": 650.5
                }
            },
        },
        404: {"description": "Keine Höhendaten verfügbar (außerhalb CH/LI)"},
        500: {"description": "Serverfehler"},
    },
)
@limiter.limit("100/minute")
async def get_elevation(
    request: Request,
    lat: float = Query(..., description="Breitengrad (WGS84)"),
    lon: float = Query(..., description="Längengrad (WGS84)"),
    geo_utils=Depends(get_geo_utils),
    api_key: str = Depends(verify_api_key),
) -> float:
    """Höhenabfrage für einen Punkt in der Schweiz."""
    elevation = geo_utils.elevation_at(lat, lon)
    if elevation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Keine Höhendaten verfügbar (außerhalb der Schweiz/Liechtenstein?).",
        )
    return elevation

@router.get(
    "/location-info",
    response_model=LocationInfoResponse,
    summary="Gemeinde und Kanton für eine Koordinate abrufen",
    description=(
        "Ermittelt Gemeinde, Kanton und weitere administrative Informationen "
        "für eine gegebene WGS84-Koordinate. Nutzt Daten von swisstopo."
    ),
    response_description="Standortinformationen (Gemeinde, Kanton, Koordinaten, Höhe)",
    responses={
        200: {
            "description": "Erfolgreiche Standortabfrage",
            "content": {
                "application/json": {
                    "example": {
                        "gemeinde": "Zürich",
                        "kanton": "Zürich",
                        "kanton_kz": "ZH",
                        "gde_nr": "261",
                        "easting": 2680000.0,
                        "northing": 1240000.0,
                        "elevation_m": 450.0,
                    }
                }
            },
        },
        500: {"description": "Serverfehler"},
    },
)
@limiter.limit("100/minute")
async def get_location_info(
    request: Request,
    lat: float = Query(..., description="Breitengrad (WGS84)"),
    lon: float = Query(..., description="Längengrad (WGS84)"),
    geo_utils=Depends(get_geo_utils),
    api_key: str = Depends(verify_api_key),
) -> LocationInfoResponse:
    """Standortinformationen für eine Koordinate."""
    try:
        info = geo_utils.location_info(lat, lon)
        return LocationInfoResponse(**info)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Standortabfrage fehlgeschlagen: {str(e)}",
        )

@router.post(
    "/building-info",
    response_model=dict,
    summary="Gebäudeinformationen für eine Adresse abrufen",
    description=(
        "Holt detaillierte Gebäude- und Wohnungsdaten aus dem amtlichen Adressregister "
        "und dem Eidgenössischen Gebäude- und Wohnungsregister (GWR). "
        "Enthält Informationen zu Heizung, Warmwasser, Baujahr, Fläche, etc."
    ),
    response_description="Gebäude- und Wohnungsdaten (GWR + Adressregister)",
    responses={
        200: {
            "description": "Erfolgreiche Gebäudeabfrage",
            "content": {
                "application/json": {
                    "example": {
                        "address": "Espenmoosstrasse 18, 9008 St. Gallen",
                        "lat": 47.4234,
                        "lon": 9.3769,
                        "easting": 2745000.0,
                        "northing": 1270000.0,
                        "egid": "CH123456789",
                        "egrid": "CH1234567890",
                        "gebaeudename": "Mustergebäude",
                        "baujahr": 1990,
                        "grundflaeche_m2": 1200.0,
                        "stockwerke": 5,
                        "heizung": {
                            "primaer": {
                                "geraet": "Wärmepumpe Luft/Wasser",
                                "energie": "Luft",
                                "stand": "2020-01-01",
                            }
                        },
                        "wohnungen": [
                            {
                                "ewid": "1",
                                "typ": "Wohnung",
                                "flaeche_m2": 100.0,
                                "zimmer": 3,
                                "baujahr": 1990,
                            }
                        ],
                    }
                }
            },
        },
        404: {"description": "Adresse nicht gefunden"},
        500: {"description": "Serverfehler"},
    },
)
@limiter.limit("50/minute")
async def get_building_info(
    request: AddressRequest,
    geo_utils=Depends(get_geo_utils),
    api_key: str = Depends(verify_api_key),
) -> dict:
    """Gebäude- und Wohnungsdaten aus GWR/Adressregister."""
    try:
        building_data = geo_utils.building_info(request.address)
        if building_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Adresse nicht gefunden.",
            )
        return building_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gebäudeabfrage fehlgeschlagen: {str(e)}",
        )