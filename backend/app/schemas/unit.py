import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UnitType


class UnitCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    symbol: str = Field(min_length=1, max_length=16)
    unit_type: UnitType
    is_active: bool = True


class UnitUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    symbol: str | None = Field(default=None, min_length=1, max_length=16)
    unit_type: UnitType | None = None
    is_active: bool | None = None


class UnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    symbol: str
    unit_type: UnitType
    is_active: bool
    created_at: datetime
    updated_at: datetime
