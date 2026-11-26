import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.order.enums import DiscountType, OrderStatus


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class OrderItemIn(BaseModel):
    product_id: uuid.UUID
    unit_id: uuid.UUID
    quantity: Decimal
    unit_price: Decimal
    discount_type: DiscountType = DiscountType.amount
    discount_value: Decimal = Decimal("0")


class OrderWrite(BaseModel):
    order_date: date
    notes: str | None = None
    discount_type: DiscountType = DiscountType.amount
    discount_value: Decimal = Decimal("0")
    items: list[OrderItemIn] = Field(min_length=1)

    @field_validator("notes")
    @classmethod
    def strip_notes(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class OrderItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name_snapshot: str
    sku_snapshot: str
    unit_id: uuid.UUID
    unit_name_snapshot: str
    quantity: Decimal
    unit_price: Decimal
    discount_type: DiscountType
    discount_value: Decimal
    discount_amount: Decimal
    subtotal: Decimal
    total: Decimal
    selling_unit_id: uuid.UUID
    selling_unit_symbol: str
    selling_price: Decimal
    quantity_unit_id: uuid.UUID | None = None
    quantity_unit_symbol: str | None = None
    quantity_unit_price: Decimal = Decimal("0")
    net_quantity: Decimal | None = None

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: uuid.UUID
    order_number: str
    status: OrderStatus
    order_date: date
    notes: str | None
    discount_type: DiscountType
    discount_value: Decimal
    subtotal: Decimal
    item_discount_total: Decimal
    order_discount_amount: Decimal
    grand_total: Decimal
    item_count: int
    total_quantity: Decimal
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    inventory_transaction_id: uuid.UUID | None
    inventory_transaction_number: str | None
    items: list[OrderItemOut]


class OrderListItem(BaseModel):
    id: uuid.UUID
    order_number: str
    status: OrderStatus
    order_date: date
    item_count: int
    grand_total: Decimal
    created_at: datetime


class OrderCatalogHit(BaseModel):
    product_id: uuid.UUID
    name: str
    sku: str
    category_id: uuid.UUID
    category_name: str
    unit_id: uuid.UUID
    unit_symbol: str
    selling_price: Decimal
    quantity_on_hand: Decimal
    quantity_unit_id: uuid.UUID | None = None
    quantity_unit_symbol: str | None = None
    quantity_unit_price: Decimal = Decimal("0")
    net_quantity: Decimal | None = None
