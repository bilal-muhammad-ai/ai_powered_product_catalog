from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Enum,
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
from app.models.enums import AttributeScope, DataType


class CategoryAttribute(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "category_attributes"
    __table_args__ = (UniqueConstraint("category_id", "code", name="uq_category_attribute_code"),)

    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    data_type: Mapped[DataType] = mapped_column(
        Enum(DataType, name="attribute_data_type", native_enum=False, length=32),
        nullable=False,
    )
    scope: Mapped[AttributeScope] = mapped_column(
        Enum(AttributeScope, name="attribute_scope", native_enum=False, length=16),
        nullable=False,
    )
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("units.id", ondelete="RESTRICT"),
        nullable=True,
    )
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    is_filterable: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    inherit_to_children: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    help_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    min_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    max_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    max_length: Mapped[int | None] = mapped_column(Integer, nullable=True)

    category: Mapped["Category"] = relationship("Category")
    unit: Mapped["Unit | None"] = relationship("Unit")
    options: Mapped[list["AttributeOption"]] = relationship(
        back_populates="attribute",
        cascade="all, delete-orphan",
        order_by="AttributeOption.sort_order",
    )


class AttributeOption(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "attribute_options"
    __table_args__ = (
        UniqueConstraint("attribute_id", "value", name="uq_attribute_option_value"),
        Index("ix_attribute_options_attribute_id", "attribute_id"),
    )

    attribute_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("category_attributes.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    value: Mapped[str] = mapped_column(String(80), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    attribute: Mapped[CategoryAttribute] = relationship(back_populates="options")
