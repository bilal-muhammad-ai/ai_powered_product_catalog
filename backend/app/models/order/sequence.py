from sqlalchemy import CheckConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OrderSequence(Base):
    __tablename__ = "order_sequences"
    __table_args__ = (CheckConstraint("last_number >= 0", name="ck_order_sequence_nonnegative"),)

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False)
