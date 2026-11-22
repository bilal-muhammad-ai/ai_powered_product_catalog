import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.enums import DataType, ProductStatus


class AttributeValueIn(BaseModel):
    attribute_id: uuid.UUID
    value: Any


class ProductWrite(BaseModel):
    category_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    sku: str = Field(min_length=1, max_length=64)
    barcode: str | None = Field(default=None, max_length=64)
    code: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=8000)
    status: ProductStatus = ProductStatus.draft
    base_unit_id: uuid.UUID | None = None
    selling_unit_id: uuid.UUID
    net_quantity: Decimal | None = Field(default=None, gt=0)
    net_quantity_unit_id: uuid.UUID | None = None
    cost_price: Decimal = Field(ge=0)
    selling_price: Decimal = Field(ge=0)
    currency_code: str = "PKR"
    slug: str | None = Field(default=None, max_length=220)
    attribute_values: list[AttributeValueIn] = Field(default_factory=list)

    @field_validator("currency_code")
    @classmethod
    def currency(cls, value: str) -> str:
        code = value.strip().upper()
        if len(code) != 3 or not code.isalpha():
            raise ValueError("Currency must be a 3-letter code")
        return code

    @field_validator("name", "sku", "barcode", "code", "slug")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class AttributeValueOut(BaseModel):
    attribute_id: uuid.UUID
    code: str
    name: str
    data_type: DataType
    value: Any


class ProductDetail(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    base_unit_id: uuid.UUID | None
    sku: str
    barcode: str | None
    name: str
    slug: str
    code: str | None
    description: str | None
    selling_unit_id: uuid.UUID
    net_quantity: Decimal | None
    net_quantity_unit_id: uuid.UUID | None
    cost_price: Decimal
    selling_price: Decimal
    currency_code: str
    status: ProductStatus
    attribute_values: list[AttributeValueOut]
    created_at: datetime
    updated_at: datetime


class ProductListItem(BaseModel):
    id: uuid.UUID
    name: str
    sku: str
    code: str | None
    slug: str
    status: ProductStatus
    category_id: uuid.UUID
    category_name: str
    selling_price: Decimal
    currency_code: str
    updated_at: datetime
