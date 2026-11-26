from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import InventoryTransactionStatus, InventoryTransactionType


class UnitConversion(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "unit_conversions"
    __table_args__ = (
        UniqueConstraint("from_unit_id", "to_unit_id", name="uq_unit_conversion_pair"),
        CheckConstraint("factor > 0", name="ck_unit_conversion_factor_positive"),
        CheckConstraint("from_unit_id <> to_unit_id", name="ck_unit_conversion_distinct"),
    )

    from_unit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("units.id", ondelete="RESTRICT"),
        nullable=False,
    )
    to_unit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("units.id", ondelete="RESTRICT"),
        nullable=False,
    )
    factor: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)

    from_unit: Mapped["Unit"] = relationship("Unit", foreign_keys=[from_unit_id])
    to_unit: Mapped["Unit"] = relationship("Unit", foreign_keys=[to_unit_id])


class InventorySequence(Base):
    __tablename__ = "inventory_sequences"
    __table_args__ = (CheckConstraint("last_number >= 0", name="ck_inventory_sequence_nonnegative"),)

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False)


class ProductStockSettings(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "product_stock_settings"
    __table_args__ = (
        UniqueConstraint("product_id", name="uq_stock_settings_product"),
        CheckConstraint(
            "minimum_stock_level IS NULL OR minimum_stock_level >= 0",
            name="ck_stock_settings_minimum",
        ),
        CheckConstraint(
            "reorder_level IS NULL OR reorder_level >= 0",
            name="ck_stock_settings_reorder",
        ),
        CheckConstraint(
            "maximum_stock_level IS NULL OR maximum_stock_level >= 0",
            name="ck_stock_settings_maximum",
        ),
        CheckConstraint(
            "maximum_stock_level IS NULL OR minimum_stock_level IS NULL OR maximum_stock_level >= minimum_stock_level",
            name="ck_stock_settings_maximum_above_minimum",
        ),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    minimum_stock_level: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    reorder_level: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    maximum_stock_level: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)

    product: Mapped["Product"] = relationship("Product")


class InventoryTransaction(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "inventory_transactions"
    __table_args__ = (
        Index("ix_inventory_transactions_status", "status"),
        Index("ix_inventory_transactions_type", "transaction_type"),
        Index("ix_inventory_transactions_date", "transaction_date"),
        Index("ix_inventory_transactions_reversal_of", "reversal_of_id"),
    )

    transaction_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    transaction_type: Mapped[InventoryTransactionType] = mapped_column(
        Enum(InventoryTransactionType, name="inventory_transaction_type", native_enum=False, length=32),
        nullable=False,
    )
    status: Mapped[InventoryTransactionStatus] = mapped_column(
        Enum(InventoryTransactionStatus, name="inventory_transaction_status", native_enum=False, length=16),
        nullable=False,
    )
    reference_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversal_of_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventory_transactions.id", ondelete="RESTRICT"),
        nullable=True,
    )

    reversal_of: Mapped[InventoryTransaction | None] = relationship(
        "InventoryTransaction",
        remote_side="InventoryTransaction.id",
    )
    items: Mapped[list[InventoryTransactionItem]] = relationship(
        back_populates="transaction",
        cascade="all, delete-orphan",
    )


class InventoryTransactionItem(UUIDMixin, Base):
    __tablename__ = "inventory_transaction_items"
    __table_args__ = (
        UniqueConstraint("transaction_id", "product_id", "unit_id", name="uq_inventory_item_product_unit"),
        CheckConstraint("quantity >= 0", name="ck_inventory_item_quantity_nonnegative"),
        CheckConstraint("unit_cost >= 0", name="ck_inventory_item_unit_cost_nonnegative"),
        CheckConstraint("total_cost >= 0", name="ck_inventory_item_total_cost_nonnegative"),
        CheckConstraint("quantity_delta <> 0", name="ck_inventory_item_delta_nonzero"),
        Index("ix_inventory_items_transaction", "transaction_id"),
        Index("ix_inventory_items_product", "product_id"),
    )

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventory_transactions.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("units.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    quantity_delta: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    transaction: Mapped[InventoryTransaction] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship("Product")
    unit: Mapped["Unit"] = relationship("Unit")


class StockBalance(UUIDMixin, Base):
    __tablename__ = "stock_balances"
    __table_args__ = (
        UniqueConstraint("product_id", name="uq_stock_balance_product"),
        CheckConstraint("quantity_on_hand >= 0", name="ck_stock_balance_quantity_nonnegative"),
        CheckConstraint("average_cost >= 0", name="ck_stock_balance_average_nonnegative"),
        CheckConstraint("inventory_value >= 0", name="ck_stock_balance_value_nonnegative"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity_on_hand: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=Decimal("0"),
        server_default="0",
    )
    average_cost: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        nullable=False,
        default=Decimal("0"),
        server_default="0",
    )
    inventory_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0"),
        server_default="0",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    product: Mapped["Product"] = relationship("Product")
