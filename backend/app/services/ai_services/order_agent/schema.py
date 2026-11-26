from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_serializer, field_validator


def _blank(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class OrderItemDraft(BaseModel):
    product_name: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None

    @field_validator("product_name", "unit", mode="before")
    @classmethod
    def blank_text(cls, value: object) -> str | None:
        return _blank(value)

    @field_validator("quantity", mode="before")
    @classmethod
    def blank_quantity(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_serializer("quantity")
    def serialize_quantity(self, value: Decimal | None) -> int | float | None:
        if value is None:
            return None
        if value == value.to_integral_value():
            return int(value)
        return float(value)


class StructuredOrder(BaseModel):
    intent: Literal["create_order"] = "create_order"
    items: list[OrderItemDraft] = Field(default_factory=list)


class ProductMatch(BaseModel):
    product_id: str
    name: str
    sku: str
    category_id: str
    category_name: str
    selling_unit_id: str
    selling_unit_symbol: str
    selling_unit_name: str
    selling_price: Decimal
    score: float


class MatchedOrderItem(OrderItemDraft):
    products: list[ProductMatch] = Field(default_factory=list)


class MatchedOrder(BaseModel):
    intent: Literal["create_order"] = "create_order"
    items: list[MatchedOrderItem] = Field(default_factory=list)
