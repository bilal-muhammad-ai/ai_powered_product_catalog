from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ProductVariant(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("product_id", "variant_key", name="uq_product_variant_key"),
        CheckConstraint("cost_price >= 0", name="ck_variant_cost_nonnegative"),
        CheckConstraint("selling_price >= 0", name="ck_variant_price_nonnegative"),
        Index("ix_product_variants_product_id", "product_id"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    selling_unit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("units.id", ondelete="RESTRICT"),
        nullable=False,
    )
    net_quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    net_quantity_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("units.id", ondelete="RESTRICT"),
        nullable=True,
    )
    cost_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    selling_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), default="PKR", server_default="PKR", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    variant_key: Mapped[str] = mapped_column(String(64), nullable=False)

    product: Mapped["Product"] = relationship("Product", back_populates="variants")
    selling_unit: Mapped["Unit"] = relationship("Unit", foreign_keys=[selling_unit_id])
    net_quantity_unit: Mapped["Unit | None"] = relationship("Unit", foreign_keys=[net_quantity_unit_id])
    attribute_values: Mapped[list["VariantAttributeValue"]] = relationship(
        back_populates="variant",
        cascade="all, delete-orphan",
    )


class VariantAttributeValue(UUIDMixin, Base):
    __tablename__ = "variant_attribute_values"
    __table_args__ = (
        UniqueConstraint("variant_id", "attribute_id", name="uq_variant_attribute_value"),
        Index("ix_vav_attr_numeric", "attribute_id", "value_numeric"),
        Index("ix_vav_attr_option", "attribute_id", "option_id"),
        Index("ix_vav_attr_text", "attribute_id", "value_text"),
    )

    variant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
    )
    attribute_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("category_attributes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_numeric: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    value_boolean: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    option_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("attribute_options.id", ondelete="RESTRICT"),
        nullable=True,
    )

    variant: Mapped[ProductVariant] = relationship(back_populates="attribute_values")
    attribute: Mapped["CategoryAttribute"] = relationship("CategoryAttribute")
    option: Mapped["AttributeOption | None"] = relationship("AttributeOption")
