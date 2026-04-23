"""Pydantic-Modelle für Compliance-Routen."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ComplianceCheckRequest(BaseModel):
    """Request für eine Compliance-Prüfung."""
    address_id: str = Field(..., description="ID der Adresse/Gebäudes")
    check_type: str = Field(
        default="full",
        description="Typ der Prüfung: 'full', 'basic', 'gwr'",
    )
    force: bool = Field(default=False, description="Cache ignorieren")

class ComplianceCheckResponse(BaseModel):
    """Response für eine Compliance-Prüfung."""
    address_id: str
    check_type: str
    status: str  # "ok", "partial", "error"
    issues: List[dict] = Field(default_factory=list, description="Liste der gefundenen Probleme")
    metadata: dict = Field(default_factory=dict, description="Zusätzliche Metadaten")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class CorrectionRequest(BaseModel):
    """Request für eine Korrektur."""
    address_id: str = Field(..., description="ID der Adresse")
    field: str = Field(..., description="Feld, das korrigiert wird (z. B. 'heizung')")
    old_value: str = Field(..., description="Alter Wert")
    new_value: str = Field(..., description="Neuer Wert")
    reason: str = Field(..., description="Begründung für die Korrektur")
    user: str = Field(..., description="Benutzer, der die Korrektur durchführt")

class DeletionRequest(BaseModel):
    """Request für eine Löschung."""
    address_id: str = Field(..., description="ID der Adresse")
    reason: str = Field(..., description="Begründung für die Löschung")
    scheduled_at: Optional[datetime] = Field(
        default=None,
        description="Zeitpunkt der Löschung (ISO-8601)",
    )
    user: str = Field(..., description="Benutzer, der die Löschung anfordert")