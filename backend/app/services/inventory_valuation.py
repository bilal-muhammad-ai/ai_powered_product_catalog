from decimal import Decimal, ROUND_HALF_UP

from app.core.exceptions import CatalogueError
from app.models.inventory import StockBalance

QTY = Decimal("0.0001")
MONEY = Decimal("0.01")
AVERAGE = Decimal("0.000001")


def q_qty(value: Decimal) -> Decimal:
    return Decimal(value).quantize(QTY, rounding=ROUND_HALF_UP)


def q_money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)


def q_avg(value: Decimal) -> Decimal:
    return Decimal(value).quantize(AVERAGE, rounding=ROUND_HALF_UP)


def apply_increase(balance: StockBalance, stock_qty: Decimal, total_cost: Decimal) -> None:
    stock_qty = q_qty(stock_qty)
    total_cost = q_money(total_cost)
    if stock_qty <= 0:
        raise CatalogueError("Quantity must be greater than zero", 422)
    if total_cost < 0:
        raise CatalogueError("Unit cost cannot be negative", 422)
    new_qty = q_qty(balance.quantity_on_hand + stock_qty)
    new_value = q_money(balance.inventory_value + total_cost)
    balance.quantity_on_hand = new_qty
    balance.inventory_value = new_value
    balance.average_cost = q_avg(new_value / new_qty)


def apply_decrease(balance: StockBalance, stock_qty: Decimal) -> tuple[Decimal, Decimal]:
    """Remove stock at the current average. Returns total cost and the 2-decimal unit cost."""
    stock_qty = q_qty(stock_qty)
    if stock_qty <= 0:
        raise CatalogueError("Quantity must be greater than zero", 422)
    if balance.quantity_on_hand < stock_qty:
        raise CatalogueError("Insufficient stock", 422)
    average = balance.average_cost
    total = q_money(stock_qty * average)
    new_qty = q_qty(balance.quantity_on_hand - stock_qty)
    if new_qty == 0:
        balance.quantity_on_hand = Decimal("0.0000")
        balance.average_cost = Decimal("0.000000")
        balance.inventory_value = Decimal("0.00")
        return total, q_money(average)
    new_value = q_money(balance.inventory_value - total)
    if new_value < 0:
        new_value = Decimal("0.00")
    balance.quantity_on_hand = new_qty
    balance.inventory_value = new_value
    return total, q_money(average)


def apply_reversal(balance: StockBalance, original_delta: Decimal, total_cost: Decimal) -> None:
    new_qty = q_qty(balance.quantity_on_hand - original_delta)
    if new_qty < 0:
        raise CatalogueError("Reversal would make stock negative", 422)
    value_change = total_cost if original_delta > 0 else -total_cost
    new_value = q_money(balance.inventory_value - value_change)
    if new_qty == 0:
        balance.quantity_on_hand = Decimal("0.0000")
        balance.average_cost = Decimal("0.000000")
        balance.inventory_value = Decimal("0.00")
        return
    if new_value < 0:
        new_value = Decimal("0.00")
    balance.quantity_on_hand = new_qty
    balance.inventory_value = new_value
    balance.average_cost = q_avg(new_value / new_qty)
