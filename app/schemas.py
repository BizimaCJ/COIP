from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CaseCreate(BaseModel):
    protected_area_id: int
    area_ha: float = Field(gt=0, examples=[14.2])
    geometry: dict[str, Any] | None = Field(
        default=None, description="GeoJSON geometry in EPSG:4326 (optional)"
    )
    created_by: int = Field(description="app_user id of whoever/whatever created the case")


class TransitionRequest(BaseModel):
    to_status: str = Field(examples=["prioritized"])
    changed_by: int = Field(examples=[1])
    reason: str = Field(min_length=3, examples=["Scored High: 14.2 ha inside the park"])


class LogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    from_status: str | None
    to_status: str
    changed_by: int
    changed_at: datetime
    reason: str


class CaseOut(BaseModel):
    id: int
    protected_area_id: int
    protected_area: str
    area_ha: float
    severity: str
    priority_code: int
    status: str
    detected_at: datetime
    closed_at: datetime | None
    allowed_next: list[str]
    geometry: dict[str, Any] | None = None
