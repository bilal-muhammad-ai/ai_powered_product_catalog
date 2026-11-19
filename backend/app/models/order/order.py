from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, ForeignKey, Index, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.order.enums import DiscountType, OrderStatus


class Order(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_status", "status"),
        Index("ix_orders_date", "order_date"),
        CheckConstraint("subtotal >= 0", name="ck_order_subtotal_nonnegative"),
        CheckConstraint("item_discount_total >= 0", name="ck_order_item_discount_nonnegative"),
        CheckConstraint("order_discount_amount >= 0", name="ck_order_discount_nonnegative"),
        CheckConstraint("discount_value >= 0", name="ck_order_discount_value_nonnegative"),
        CheckConstraint("grand_total >= 0", name="ck_order_grand_nonnegative"),
    )

    order_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status", native_enum=False, length=16),
        nullable=False,
        default=OrderStatus.draft,
    )
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    item_discount_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    discount_type: Mapped[DiscountType] = mapped_column(
        Enum(DiscountType, name="order_discount_type", native_enum=False, length=16),
        nullable=False,
        default=DiscountType.amount,
    )
    discount_value: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=0)
    order_discount_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    inventory_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventory_transactions.id", ondelete="RESTRICT"),
        unique=True,
        nullable=True,
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )
    inventory_transaction: Mapped["InventoryTransaction | None"] = relationship("InventoryTransaction")
