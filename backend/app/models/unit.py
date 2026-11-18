from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import UnitType


class Unit(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "units"

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    symbol: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    unit_type: Mapped[UnitType] = mapped_column(
        Enum(UnitType, name="unit_type", native_enum=False, length=32),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
