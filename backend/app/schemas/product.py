import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.enums import DataType, ProductStatus


class AttributeValueIn(BaseModel):
    attribute_id: uuid.UUID
    value: Any


class VariantIn(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    barcode: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, max_length=200)
    selling_unit_id: uuid.UUID
    net_quantity: Decimal | None = Field(default=None, gt=0)
    net_quantity_unit_id: uuid.UUID | None = None
    cost_price: Decimal = Field(ge=0)
    selling_price: Decimal = Field(ge=0)
    currency_code: str = "PKR"
    is_active: bool = True
    sort_order: int = 0
    attribute_values: list[AttributeValueIn] = Field(default_factory=list)

    @field_validator("currency_code")
    @classmethod
    def currency(cls, value: str) -> str:
        code = value.strip().upper()
        if len(code) != 3 or not code.isalpha():
            raise ValueError("Currency must be a 3-letter code")
        return code

    @field_validator("sku", "barcode", "name")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ProductWrite(BaseModel):
    category_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    code: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=8000)
    status: ProductStatus = ProductStatus.draft
    base_unit_id: uuid.UUID | None = None
    slug: str | None = Field(default=None, max_length=220)
    attribute_values: list[AttributeValueIn] = Field(default_factory=list)
    variants: list[VariantIn] = Field(min_length=1)

    @field_validator("name", "code", "slug")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class VariantPatch(BaseModel):
    barcode: str | None = Field(default=None, max_length=64)
    cost_price: Decimal | None = Field(default=None, ge=0)
    selling_price: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None

    @field_validator("barcode")
    @classmethod
    def strip_barcode(cls, value: str | None) -> str | None:
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


class VariantOut(BaseModel):
    id: uuid.UUID
    sku: str
    barcode: str | None
    name: str | None
    selling_unit_id: uuid.UUID
    net_quantity: Decimal | None
    net_quantity_unit_id: uuid.UUID | None
    cost_price: Decimal
    selling_price: Decimal
    currency_code: str
    is_active: bool
    sort_order: int
    variant_key: str
    attribute_values: list[AttributeValueOut]


class ProductDetail(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    base_unit_id: uuid.UUID | None
    name: str
    slug: str
    code: str | None
    description: str | None
    status: ProductStatus
    attribute_values: list[AttributeValueOut]
    variants: list[VariantOut]
    created_at: datetime
    updated_at: datetime


class ProductListItem(BaseModel):
    id: uuid.UUID
    name: str
    code: str | None
    slug: str
    status: ProductStatus
    category_id: uuid.UUID
    category_name: str
    variant_count: int
    selling_price_min: Decimal | None
    selling_price_max: Decimal | None
    updated_at: datetime


class VariantDetail(VariantOut):
    product_id: uuid.UUID
