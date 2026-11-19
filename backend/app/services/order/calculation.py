"""Order totals. This module does not read or write the database."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.core.exceptions import CatalogueError
from app.models.order.enums import DiscountType

MONEY = Decimal("0.01")
VALUE = Decimal("0.0001")


def q_money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)


def q_value(value: Decimal) -> Decimal:
    return Decimal(value).quantize(VALUE, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class LineAmounts:
    subtotal: Decimal
    discount_amount: Decimal
    total: Decimal


@dataclass(frozen=True)
class OrderAmounts:
    lines: list[LineAmounts]
    subtotal: Decimal
    item_discount_total: Decimal
    order_discount_amount: Decimal
    grand_total: Decimal


def discount_amount(base: Decimal, discount_type: DiscountType, discount_value: Decimal) -> Decimal:
    if discount_value < 0:
        raise CatalogueError("Discount cannot be negative", 422)
    if discount_type == DiscountType.percent:
        amount = q_money(base * discount_value / Decimal(100))
    else:
        amount = q_money(discount_value)
    if amount > base:
        raise CatalogueError("Discount cannot exceed the amount it applies to", 422)
    return amount


def line_amounts(quantity: Decimal, unit_price: Decimal, discount_type: DiscountType, discount_value: Decimal) -> LineAmounts:
    if quantity <= 0:
        raise CatalogueError("Quantity must be greater than zero", 422)
    if unit_price < 0:
        raise CatalogueError("Unit price cannot be negative", 422)
    subtotal = q_money(quantity * unit_price)
    discount = discount_amount(subtotal, discount_type, discount_value)
    return LineAmounts(subtotal=subtotal, discount_amount=discount, total=q_money(subtotal - discount))


def order_amounts(
    lines: list[tuple[Decimal, Decimal, DiscountType, Decimal]],
    discount_type: DiscountType,
    discount_value: Decimal,
) -> OrderAmounts:
    priced = [line_amounts(quantity, price, kind, value) for quantity, price, kind, value in lines]
    subtotal = q_money(sum((line.subtotal for line in priced), Decimal("0")))
    item_discount_total = q_money(sum((line.discount_amount for line in priced), Decimal("0")))
    net = q_money(subtotal - item_discount_total)
    order_discount = discount_amount(net, discount_type, discount_value)
    return OrderAmounts(
        lines=priced,
        subtotal=subtotal,
        item_discount_total=item_discount_total,
        order_discount_amount=order_discount,
        grand_total=q_money(net - order_discount),
    )
