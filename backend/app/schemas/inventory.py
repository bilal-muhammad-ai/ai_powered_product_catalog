import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import InventoryTransactionStatus, InventoryTransactionType, StockStatus


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class TransactionItemIn(BaseModel):
    product_id: uuid.UUID
    unit_id: uuid.UUID
    quantity: Decimal | None = None
    physical_quantity: Decimal | None = None
    unit_cost: Decimal | None = None


class TransactionWrite(BaseModel):
    transaction_type: InventoryTransactionType
    transaction_date: date
    reference_number: str | None = Field(default=None, max_length=64)
    reference_type: str | None = Field(default=None, max_length=32)
    reference_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=4000)
    reason: str | None = Field(default=None, max_length=200)
    items: list[TransactionItemIn] = Field(min_length=1)
    post: bool = False

    @field_validator("reference_number", "reference_type", "notes", "reason")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class MovementWrite(BaseModel):
    transaction_date: date
    reference_number: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=4000)
    reason: str | None = Field(default=None, max_length=200)
    items: list[TransactionItemIn] = Field(min_length=1)
    post: bool = False

    @field_validator("reference_number", "notes", "reason")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return _blank_to_none(value)

    def as_transaction(self, transaction_type: InventoryTransactionType) -> TransactionWrite:
        return TransactionWrite(transaction_type=transaction_type, **self.model_dump())


class TransactionUpdate(BaseModel):
    transaction_date: date
    reference_number: str | None = Field(default=None, max_length=64)
    reference_type: str | None = Field(default=None, max_length=32)
    reference_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=4000)
    reason: str | None = Field(default=None, max_length=200)
    items: list[TransactionItemIn] = Field(min_length=1)

    @field_validator("reference_number", "reference_type", "notes", "reason")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class TransactionItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    sku: str
    unit_id: uuid.UUID
    unit_symbol: str
    quantity: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    quantity_delta: Decimal


class TransactionOut(BaseModel):
    id: uuid.UUID
    transaction_number: str
    transaction_type: InventoryTransactionType
    status: InventoryTransactionStatus
    reference_number: str | None
    reference_type: str | None
    reference_id: uuid.UUID | None
    transaction_date: date
    notes: str | None
    reason: str | None
    created_by: uuid.UUID | None
    created_at: datetime
    posted_at: datetime | None
    reversed_at: datetime | None
    reversal_of_id: uuid.UUID | None
    item_count: int
    total_quantity: Decimal
    total_value: Decimal
    items: list[TransactionItemOut] = Field(default_factory=list)


class TransactionListItem(BaseModel):
    id: uuid.UUID
    transaction_number: str
    transaction_type: InventoryTransactionType
    status: InventoryTransactionStatus
    transaction_date: date
    reference_number: str | None
    item_count: int
    total_quantity: Decimal
    total_value: Decimal


class BalanceItem(BaseModel):
    product_id: uuid.UUID
    product_name: str
    sku: str
    category_id: uuid.UUID
    category_name: str
    brand: str | None
    quantity_on_hand: Decimal
    unit_id: uuid.UUID
    unit_symbol: str
    average_cost: Decimal
    inventory_value: Decimal
    minimum_stock_level: Decimal | None
    reorder_level: Decimal | None = None
    maximum_stock_level: Decimal | None = None
    stock_status: StockStatus


class InventoryDetail(BalanceItem):
    cost_price: Decimal
    currency_code: str
    barcode: str | None
    net_quantity: Decimal | None
    net_quantity_unit_symbol: str | None


class MovementOut(BaseModel):
    transaction_id: uuid.UUID
    transaction_number: str
    transaction_type: InventoryTransactionType
    status: InventoryTransactionStatus
    transaction_date: date
    quantity: Decimal
    quantity_delta: Decimal
    unit_symbol: str
    unit_cost: Decimal
    total_cost: Decimal
    reference_number: str | None


class CategoryValue(BaseModel):
    category_name: str
    inventory_value: Decimal


class TypeCount(BaseModel):
    transaction_type: InventoryTransactionType
    count: int


class InventorySummary(BaseModel):
    product_count: int
    total_quantity: Decimal
    total_value: Decimal
    low_stock_count: int
    out_of_stock_count: int
    recent_transactions: list[TransactionListItem]
    low_stock: list[BalanceItem]
    out_of_stock: list[BalanceItem]
    value_by_category: list[CategoryValue]
    movement_counts: list[TypeCount]


class CatalogHit(BaseModel):
    product_id: uuid.UUID
    name: str
    sku: str
    category_name: str
    brand: str | None
    unit_id: uuid.UUID
    unit_symbol: str
    quantity_on_hand: Decimal
    average_cost: Decimal
    net_quantity: Decimal | None
    net_quantity_unit_id: uuid.UUID | None


class StockSettingsIn(BaseModel):
    minimum_stock_level: Decimal | None = None
    reorder_level: Decimal | None = None
    maximum_stock_level: Decimal | None = None


class StockSettingsOut(StockSettingsIn):
    product_id: uuid.UUID


class ReportRow(BaseModel):
    cells: list[str]
