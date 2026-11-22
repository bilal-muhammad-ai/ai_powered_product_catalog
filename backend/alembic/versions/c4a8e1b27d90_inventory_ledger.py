"""inventory ledger

Revision ID: c4a8e1b27d90
Revises: 2cd08a8c6b5d
Create Date: 2026-11-18 17:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4a8e1b27d90"
down_revision: Union[str, Sequence[str], None] = "2cd08a8c6b5d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "unit_conversions",
        sa.Column("from_unit_id", sa.Uuid(), nullable=False),
        sa.Column("to_unit_id", sa.Uuid(), nullable=False),
        sa.Column("factor", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("factor > 0", name="ck_unit_conversion_factor_positive"),
        sa.CheckConstraint("from_unit_id <> to_unit_id", name="ck_unit_conversion_distinct"),
        sa.ForeignKeyConstraint(["from_unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["to_unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("from_unit_id", "to_unit_id", name="uq_unit_conversion_pair"),
    )
    op.create_table(
        "inventory_sequences",
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("last_number", sa.Integer(), nullable=False),
        sa.CheckConstraint("last_number >= 0", name="ck_inventory_sequence_nonnegative"),
        sa.PrimaryKeyConstraint("year"),
    )
    op.create_table(
        "product_stock_settings",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("minimum_stock_level", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("reorder_level", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("maximum_stock_level", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("minimum_stock_level IS NULL OR minimum_stock_level >= 0", name="ck_stock_settings_minimum"),
        sa.CheckConstraint("reorder_level IS NULL OR reorder_level >= 0", name="ck_stock_settings_reorder"),
        sa.CheckConstraint("maximum_stock_level IS NULL OR maximum_stock_level >= 0", name="ck_stock_settings_maximum"),
        sa.CheckConstraint(
            "maximum_stock_level IS NULL OR minimum_stock_level IS NULL OR maximum_stock_level >= minimum_stock_level",
            name="ck_stock_settings_maximum_above_minimum",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", name="uq_stock_settings_product"),
    )
    op.create_table(
        "inventory_transactions",
        sa.Column("transaction_number", sa.String(length=32), nullable=False),
        sa.Column(
            "transaction_type",
            sa.Enum(
                "OPENING_STOCK",
                "STOCK_RECEIPT",
                "STOCK_ISSUE",
                "STOCK_ADJUSTMENT",
                "REVERSAL",
                name="inventory_transaction_type",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "POSTED",
                "CANCELLED",
                "REVERSED",
                name="inventory_transaction_status",
                native_enum=False,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("reference_number", sa.String(length=64), nullable=True),
        sa.Column("reference_type", sa.String(length=32), nullable=True),
        sa.Column("reference_id", sa.Uuid(), nullable=True),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversal_of_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["reversal_of_id"], ["inventory_transactions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_number"),
    )
    op.create_index("ix_inventory_transactions_status", "inventory_transactions", ["status"], unique=False)
    op.create_index("ix_inventory_transactions_type", "inventory_transactions", ["transaction_type"], unique=False)
    op.create_index("ix_inventory_transactions_date", "inventory_transactions", ["transaction_date"], unique=False)
    op.create_index("ix_inventory_transactions_reversal_of", "inventory_transactions", ["reversal_of_id"], unique=False)
    op.create_table(
        "inventory_transaction_items",
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("unit_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("unit_cost", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("total_cost", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("quantity_delta", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("quantity >= 0", name="ck_inventory_item_quantity_nonnegative"),
        sa.CheckConstraint("unit_cost >= 0", name="ck_inventory_item_unit_cost_nonnegative"),
        sa.CheckConstraint("total_cost >= 0", name="ck_inventory_item_total_cost_nonnegative"),
        sa.CheckConstraint("quantity_delta <> 0", name="ck_inventory_item_delta_nonzero"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["transaction_id"], ["inventory_transactions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_id", "product_id", name="uq_inventory_item_product"),
    )
    op.create_index("ix_inventory_items_transaction", "inventory_transaction_items", ["transaction_id"], unique=False)
    op.create_index("ix_inventory_items_product", "inventory_transaction_items", ["product_id"], unique=False)
    op.create_table(
        "stock_balances",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("quantity_on_hand", sa.Numeric(precision=14, scale=4), server_default="0", nullable=False),
        sa.Column("average_cost", sa.Numeric(precision=18, scale=6), server_default="0", nullable=False),
        sa.Column("inventory_value", sa.Numeric(precision=14, scale=2), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("quantity_on_hand >= 0", name="ck_stock_balance_quantity_nonnegative"),
        sa.CheckConstraint("average_cost >= 0", name="ck_stock_balance_average_nonnegative"),
        sa.CheckConstraint("inventory_value >= 0", name="ck_stock_balance_value_nonnegative"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", name="uq_stock_balance_product"),
    )


def downgrade() -> None:
    op.drop_table("stock_balances")
    op.drop_index("ix_inventory_items_product", table_name="inventory_transaction_items")
    op.drop_index("ix_inventory_items_transaction", table_name="inventory_transaction_items")
    op.drop_table("inventory_transaction_items")
    op.drop_index("ix_inventory_transactions_reversal_of", table_name="inventory_transactions")
    op.drop_index("ix_inventory_transactions_date", table_name="inventory_transactions")
    op.drop_index("ix_inventory_transactions_type", table_name="inventory_transactions")
    op.drop_index("ix_inventory_transactions_status", table_name="inventory_transactions")
    op.drop_table("inventory_transactions")
    op.drop_table("product_stock_settings")
    op.drop_table("inventory_sequences")
    op.drop_table("unit_conversions")
