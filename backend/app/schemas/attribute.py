import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AttributeScope, DataType


class AttributeOptionCreate(BaseModel):
    label: str = Field(min_length=1, max_length=160)
    value: str | None = Field(default=None, max_length=80)
    sort_order: int = 0
    is_active: bool = True


class AttributeOptionUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=160)
    value: str | None = Field(default=None, max_length=80)
    sort_order: int | None = None
    is_active: bool | None = None


class AttributeOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    attribute_id: uuid.UUID
    label: str
    value: str
    sort_order: int
    is_active: bool


class AttributeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    code: str | None = Field(default=None, max_length=80)
    data_type: DataType
    scope: AttributeScope
    unit_id: uuid.UUID | None = None
    is_required: bool = False
    is_filterable: bool = False
    is_active: bool = True
    inherit_to_children: bool = True
    sort_order: int = 0
    help_text: str | None = Field(default=None, max_length=2000)
    min_value: Decimal | None = None
    max_value: Decimal | None = None
    max_length: int | None = Field(default=None, ge=1)


class AttributeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    code: str | None = Field(default=None, max_length=80)
    data_type: DataType | None = None
    scope: AttributeScope | None = None
    unit_id: uuid.UUID | None = None
    is_required: bool | None = None
    is_filterable: bool | None = None
    is_active: bool | None = None
    inherit_to_children: bool | None = None
    sort_order: int | None = None
    help_text: str | None = Field(default=None, max_length=2000)
    min_value: Decimal | None = None
    max_value: Decimal | None = None
    max_length: int | None = Field(default=None, ge=1)
    clear_unit: bool = False


class AttributeOut(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    owner_category_name: str
    code: str
    name: str
    data_type: DataType
    scope: AttributeScope
    unit_id: uuid.UUID | None
    is_required: bool
    is_filterable: bool
    is_active: bool
    inherit_to_children: bool
    sort_order: int
    help_text: str | None
    min_value: Decimal | None
    max_value: Decimal | None
    max_length: int | None
    inherited: bool
    options: list[AttributeOptionOut]
    created_at: datetime
    updated_at: datetime
