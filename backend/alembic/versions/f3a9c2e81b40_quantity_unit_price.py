"""quantity unit price

Revision ID: f3a9c2e81b40
Revises: e7b1c4d9a2f0
Create Date: 2026-11-26 12:59:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a9c2e81b40"
down_revision: Union[str, Sequence[str], None] = "e7b1c4d9a2f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("quantity_unit_price", sa.Numeric(precision=14, scale=2), server_default="0", nullable=False),
    )
    op.create_check_constraint("ck_product_quantity_price_nonnegative", "products", "quantity_unit_price >= 0")
    op.drop_constraint("uq_inventory_item_product", "inventory_transaction_items", type_="unique")
    op.create_unique_constraint(
        "uq_inventory_item_product_unit",
        "inventory_transaction_items",
        ["transaction_id", "product_id", "unit_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_inventory_item_product_unit", "inventory_transaction_items", type_="unique")
    op.create_unique_constraint(
        "uq_inventory_item_product",
        "inventory_transaction_items",
        ["transaction_id", "product_id"],
    )
    op.drop_constraint("ck_product_quantity_price_nonnegative", "products", type_="check")
    op.drop_column("products", "quantity_unit_price")
