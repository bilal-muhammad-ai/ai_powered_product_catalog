"""orders

Revision ID: e7b1c4d9a2f0
Revises: c4a8e1b27d90
Create Date: 2026-11-19 11:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7b1c4d9a2f0"
down_revision: Union[str, Sequence[str], None] = "c4a8e1b27d90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

discount_type = sa.Enum("AMOUNT", "PERCENT", name="order_discount_type", native_enum=False, length=16)
order_status = sa.Enum(
    "DRAFT",
    "CONFIRMED",
    "COMPLETED",
    "CANCELLED",
    name="order_status",
    native_enum=False,
    length=16,
)


def upgrade() -> None:
    op.create_table(
        "order_sequences",
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("last_number", sa.Integer(), nullable=False),
        sa.CheckConstraint("last_number >= 0", name="ck_order_sequence_nonnegative"),
        sa.PrimaryKeyConstraint("year"),
    )
    op.create_table(
        "orders",
        sa.Column("order_number", sa.String(length=32), nullable=False),
        sa.Column("status", order_status, nullable=False),
        sa.Column("order_date", sa.Date(), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("item_discount_total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("discount_type", discount_type, nullable=False),
        sa.Column("discount_value", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("order_discount_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("grand_total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("inventory_transaction_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("subtotal >= 0", name="ck_order_subtotal_nonnegative"),
        sa.CheckConstraint("item_discount_total >= 0", name="ck_order_item_discount_nonnegative"),
        sa.CheckConstraint("order_discount_amount >= 0", name="ck_order_discount_nonnegative"),
        sa.CheckConstraint("discount_value >= 0", name="ck_order_discount_value_nonnegative"),
        sa.CheckConstraint("grand_total >= 0", name="ck_order_grand_nonnegative"),
        sa.ForeignKeyConstraint(["inventory_transaction_id"], ["inventory_transactions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_number"),
        sa.UniqueConstraint("inventory_transaction_id"),
    )
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_date", "orders", ["order_date"])
    op.create_table(
        "order_items",
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("product_name_snapshot", sa.String(length=200), nullable=False),
        sa.Column("sku_snapshot", sa.String(length=64), nullable=False),
        sa.Column("unit_id", sa.Uuid(), nullable=False),
        sa.Column("unit_name_snapshot", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("discount_type", discount_type, nullable=False),
        sa.Column("discount_value", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("discount_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_order_item_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_order_item_price_nonnegative"),
        sa.CheckConstraint("discount_value >= 0", name="ck_order_item_discount_value_nonnegative"),
        sa.CheckConstraint("discount_amount >= 0", name="ck_order_item_discount_nonnegative"),
        sa.CheckConstraint("subtotal >= 0", name="ck_order_item_subtotal_nonnegative"),
        sa.CheckConstraint("total >= 0", name="ck_order_item_total_nonnegative"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_date", table_name="orders")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_table("orders")
    op.drop_table("order_sequences")
