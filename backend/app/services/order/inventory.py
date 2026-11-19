"""Confirm and cancel orders through the inventory ledger."""

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import CatalogueError
from app.models.enums import InventoryTransactionType
from app.models.order.enums import OrderStatus
from app.models.order.order import Order
from app.models.product import Product
from app.schemas.inventory import TransactionItemIn, TransactionWrite
from app.services.inventory_transactions import create_transaction, reverse_transaction
from app.services.inventory_valuation import q_qty
from app.services.unit_conversion import to_selling_quantity


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _lock(db: Session, order_id: uuid.UUID) -> Order:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise CatalogueError("Order not found", 404)
    return order


def confirm_order(db: Session, order: Order) -> Order:
    locked = _lock(db, order.id)
    if locked.status != OrderStatus.draft:
        raise CatalogueError("Only a draft order can be confirmed", 409)
    if not locked.items:
        raise CatalogueError("Add at least one product", 422)
    merged: dict[uuid.UUID, Decimal] = defaultdict(lambda: Decimal("0"))
    selling_units: dict[uuid.UUID, uuid.UUID] = {}
    for item in locked.items:
        product = db.get(Product, item.product_id)
        if product is None:
            raise CatalogueError("Product not found", 404)
        merged[product.id] += to_selling_quantity(db, product, item.unit_id, item.quantity)
        selling_units[product.id] = product.selling_unit_id
    lines = [
        TransactionItemIn(product_id=product_id, unit_id=selling_units[product_id], quantity=q_qty(quantity))
        for product_id, quantity in merged.items()
        if quantity > 0
    ]
    if not lines:
        raise CatalogueError("Quantity must be greater than zero", 422)
    transaction = create_transaction(
        db,
        TransactionWrite(
            transaction_type=InventoryTransactionType.stock_issue,
            transaction_date=locked.order_date,
            reference_number=locked.order_number,
            reference_type="order",
            reference_id=locked.id,
            reason=f"Order {locked.order_number}",
            items=lines,
            post=True,
        ),
    )
    locked.status = OrderStatus.confirmed
    locked.confirmed_at = _now()
    locked.inventory_transaction_id = transaction.id
    db.flush()
    return locked


def cancel_order(db: Session, order: Order) -> Order:
    locked = _lock(db, order.id)
    if locked.status != OrderStatus.confirmed:
        raise CatalogueError("Only a confirmed order can be cancelled", 409)
    if locked.inventory_transaction_id is None:
        raise CatalogueError("This order has no stock issue to reverse", 409)
    reverse_transaction(db, locked.inventory_transaction_id)
    locked.status = OrderStatus.cancelled
    locked.cancelled_at = _now()
    db.flush()
    return locked
