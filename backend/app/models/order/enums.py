import enum


class OrderStatus(str, enum.Enum):
    draft = "DRAFT"
    confirmed = "CONFIRMED"
    completed = "COMPLETED"
    cancelled = "CANCELLED"


class DiscountType(str, enum.Enum):
    amount = "AMOUNT"
    percent = "PERCENT"
