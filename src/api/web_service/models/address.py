"""Pydantic-Modelle für Adressen und Geodaten."""

from pydantic import BaseModel, Field
from typing import Optional

class AddressResponse(BaseModel):
    """Response-Modell für Geocoding-Ergebnisse."""
    label: str = Field(..., description="Anzeigename der Adresse/des Orts")
    lat: Optional[float] = Field(None, description="Breitengrad (WGS84)")
    lon: Optional[float] = Field(None, description="Längengrad (WGS84)")
    easting: Optional[float] = Field(None, description="LV95-Ostwert")
    northing: Optional[float] = Field(None, description="LV95-Nordwert")
    origin: Optional[str] = Field(None, description="Quelle (z. B. 'address', 'gg25')")
    detail: str = Field(default="", description="Zusätzliche Details")
    zip_code: Optional[str] = Field(None, description="Postleitzahl")
    city: Optional[str] = Field(None, description="Ort/Gemeinde")
    egid: Optional[str] = Field(None, description="EGID (Eidgenössische Gebäude-Identifikator)")
    feature_id: Optional[str] = Field(None, description="Feature-ID (GeoAdmin)")

class LocationInfoResponse(BaseModel):
    """Response-Modell für Standortinformationen."""
    gemeinde: Optional[str] = Field(None, description="Gemeindename")
    kanton: Optional[str] = Field(None, description="Kanton (Name)")
    kanton_kz: Optional[str] = Field(None, description="Kanton (Kürzel, z. B. 'ZH')")
    gde_nr: Optional[str] = Field(None, description="Gemeinde-Nummer (BFS)")
    easting: float = Field(..., description="LV95-Ostwert")
    northing: float = Field(..., description="LV95-Nordwert")
    elevation_m: Optional[float] = Field(None, description="Höhe über Meer (m)")

class AddressRequest(BaseModel):
    """Request-Modell für Adressabfragen."""
    address: str = Field(..., description="Schweizer Adresse (z. B. 'Espenmoosstrasse 18, 9008 St. Gallen')")