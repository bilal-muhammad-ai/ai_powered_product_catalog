"""make product sku optional

Revision ID: a8f3c1d94e20
Revises: b7e4d1a90c26
Create Date: 2026-11-28 10:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8f3c1d94e20"
down_revision: Union[str, Sequence[str], None] = "b7e4d1a90c26"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("products", "sku", existing_type=sa.String(length=64), nullable=True)


def downgrade() -> None:
    op.execute(
        "UPDATE products SET sku = 'SKU-' || substr(id::text, 1, 8) WHERE sku IS NULL"
    )
    op.alter_column("products", "sku", existing_type=sa.String(length=64), nullable=False)
