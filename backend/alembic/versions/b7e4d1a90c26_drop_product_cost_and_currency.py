"""drop product cost price and currency

Revision ID: b7e4d1a90c26
Revises: f3a9c2e81b40
Create Date: 2026-11-26 18:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e4d1a90c26"
down_revision: Union[str, Sequence[str], None] = "f3a9c2e81b40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_product_cost_nonnegative", "products", type_="check")
    op.drop_column("products", "cost_price")
    op.drop_column("products", "currency_code")


def downgrade() -> None:
    op.add_column(
        "products",
        sa.Column("currency_code", sa.String(length=3), server_default="PKR", nullable=False),
    )
    op.add_column(
        "products",
        sa.Column("cost_price", sa.Numeric(precision=14, scale=2), server_default="0", nullable=False),
    )
    op.alter_column("products", "cost_price", server_default=None)
    op.create_check_constraint("ck_product_cost_nonnegative", "products", "cost_price >= 0")
