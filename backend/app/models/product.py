from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import ProductStatus


class Product(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_category_id", "category_id"),
        Index("ix_products_status", "status"),
        CheckConstraint("selling_price >= 0", name="ck_product_price_nonnegative"),
        CheckConstraint("quantity_unit_price >= 0", name="ck_product_quantity_price_nonnegative"),
        CheckConstraint("net_quantity IS NULL OR net_quantity > 0", name="ck_product_net_quantity_positive"),
        CheckConstraint(
            "net_quantity IS NULL OR net_quantity_unit_id IS NOT NULL",
            name="ck_product_net_quantity_unit",
        ),
    )

    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    base_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("units.id", ondelete="RESTRICT"),
        nullable=True,
    )
    sku: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), unique=True, nullable=False)
    code: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    selling_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    quantity_unit_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0"),
        server_default="0",
    )
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status", native_enum=False, length=16),
        nullable=False,
        default=ProductStatus.draft,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    category: Mapped["Category"] = relationship("Category")
    base_unit: Mapped["Unit | None"] = relationship("Unit", foreign_keys=[base_unit_id])
    selling_unit: Mapped["Unit"] = relationship("Unit", foreign_keys=[selling_unit_id])
    net_quantity_unit: Mapped["Unit | None"] = relationship("Unit", foreign_keys=[net_quantity_unit_id])
    attribute_values: Mapped[list["ProductAttributeValue"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )
    multi_options: Mapped[list["ProductAttributeMultiOption"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )


class ProductAttributeValue(UUIDMixin, Base):
    __tablename__ = "product_attribute_values"
    __table_args__ = (
        UniqueConstraint("product_id", "attribute_id", name="uq_product_attribute_value"),
        Index("ix_pav_attr_numeric", "attribute_id", "value_numeric"),
        Index("ix_pav_attr_option", "attribute_id", "option_id"),
        Index("ix_pav_attr_text", "attribute_id", "value_text"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
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

    product: Mapped[Product] = relationship(back_populates="attribute_values")
    attribute: Mapped["CategoryAttribute"] = relationship("CategoryAttribute")
    option: Mapped["AttributeOption | None"] = relationship("AttributeOption")


class ProductAttributeMultiOption(Base):
    __tablename__ = "product_attribute_multi_options"

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    attribute_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("category_attributes.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    option_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("attribute_options.id", ondelete="RESTRICT"),
        primary_key=True,
    )

    product: Mapped[Product] = relationship(back_populates="multi_options")
    attribute: Mapped["CategoryAttribute"] = relationship("CategoryAttribute")
    option: Mapped["AttributeOption"] = relationship("AttributeOption")
