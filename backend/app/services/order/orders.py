from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import CatalogueError
from app.models.enums import ProductStatus
from app.models.order.enums import OrderStatus
from app.models.order.item import OrderItem
from app.models.order.order import Order
from app.models.order.sequence import OrderSequence
from app.models.product import Product
from app.models.unit import Unit
from app.schemas.order.order import OrderItemIn, OrderItemOut, OrderListItem, OrderOut, OrderWrite
from app.services.inventory_valuation import q_qty
from app.services.order import inventory as order_inventory
from app.services.order.calculation import order_amounts, q_money, q_value
from app.services.unit_conversion import to_selling_quantity

SORTS = {
    "order_date": Order.order_date,
    "order_number": Order.order_number,
    "grand_total": Order.grand_total,
    "created_at": Order.created_at,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _like(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def next_order_number(db: Session, on: date) -> str:
    year = on.year
    db.execute(pg_insert(OrderSequence).values(year=year, last_number=0).on_conflict_do_nothing(index_elements=["year"]))
    row = db.scalar(select(OrderSequence).where(OrderSequence.year == year).with_for_update())
    if row is None:
        raise CatalogueError("Could not allocate an order number", 409)
    row.last_number += 1
    db.flush()
    return f"ORD-{year}-{row.last_number:06d}"


def _load(db: Session, order_id: uuid.UUID) -> Order:
    order = db.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items), selectinload(Order.inventory_transaction))
    )
    if order is None:
        raise CatalogueError("Order not found", 404)
    return order


def _lock(db: Session, order_id: uuid.UUID) -> Order:
    locked = db.scalar(select(Order.id).where(Order.id == order_id).with_for_update())
    if locked is None:
        raise CatalogueError("Order not found", 404)
    return _load(db, order_id)


def _active_product(db: Session, product_id: uuid.UUID) -> Product:
    product = db.get(Product, product_id)
    if product is None or product.deleted_at is not None:
        raise CatalogueError("Product not found", 404)
    if product.status != ProductStatus.active:
        raise CatalogueError("Product is not active", 422)
    return product


def _build_item(db: Session, data: OrderItemIn) -> OrderItem:
    product = _active_product(db, data.product_id)
    unit = db.get(Unit, data.unit_id)
    if unit is None:
        raise CatalogueError("Unit not found", 422)
    if not unit.is_active:
        raise CatalogueError("Unit is inactive", 422)
    if data.quantity <= 0:
        raise CatalogueError("Quantity must be greater than zero", 422)
    if data.unit_price < 0:
        raise CatalogueError("Unit price cannot be negative", 422)
    to_selling_quantity(db, product, unit.id, data.quantity)
    return OrderItem(
        product_id=product.id,
        product_name_snapshot=product.name,
        sku_snapshot=product.sku,
        unit_id=unit.id,
        unit_name_snapshot=unit.symbol,
        quantity=q_qty(data.quantity),
        unit_price=q_money(data.unit_price),
        discount_type=data.discount_type,
        discount_value=q_value(data.discount_value),
        discount_amount=Decimal("0.00"),
        subtotal=Decimal("0.00"),
        total=Decimal("0.00"),
    )


def _apply_totals(order: Order) -> None:
    amounts = order_amounts(
        [(item.quantity, item.unit_price, item.discount_type, item.discount_value) for item in order.items],
        order.discount_type,
        order.discount_value,
    )
    for item, line in zip(order.items, amounts.lines, strict=True):
        item.subtotal = line.subtotal
        item.discount_amount = line.discount_amount
        item.total = line.total
    order.subtotal = amounts.subtotal
    order.item_discount_total = amounts.item_discount_total
    order.order_discount_amount = amounts.order_discount_amount
    order.grand_total = amounts.grand_total


def _replace_items(db: Session, order: Order, items: list[OrderItem]) -> None:
    order.items.clear()
    db.flush()
    for item in items:
        order.items.append(item)
    db.flush()


def to_order_out(order: Order) -> OrderOut:
    quantity = q_qty(sum((item.quantity for item in order.items), Decimal("0")))
    transaction = order.inventory_transaction
    return OrderOut(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        order_date=order.order_date,
        notes=order.notes,
        discount_type=order.discount_type,
        discount_value=order.discount_value,
        subtotal=order.subtotal,
        item_discount_total=order.item_discount_total,
        order_discount_amount=order.order_discount_amount,
        grand_total=order.grand_total,
        item_count=len(order.items),
        total_quantity=quantity,
        confirmed_at=order.confirmed_at,
        cancelled_at=order.cancelled_at,
        completed_at=order.completed_at,
        created_at=order.created_at,
        updated_at=order.updated_at,
        inventory_transaction_id=order.inventory_transaction_id,
        inventory_transaction_number=None if transaction is None else transaction.transaction_number,
        items=[OrderItemOut.model_validate(item) for item in order.items],
    )


def create_order(db: Session, data: OrderWrite) -> Order:
    items = [_build_item(db, line) for line in data.items]
    order = Order(
        order_number=next_order_number(db, data.order_date),
        status=OrderStatus.draft,
        order_date=data.order_date,
        notes=data.notes,
        discount_type=data.discount_type,
        discount_value=q_value(data.discount_value),
        subtotal=Decimal("0.00"),
        item_discount_total=Decimal("0.00"),
        order_discount_amount=Decimal("0.00"),
        grand_total=Decimal("0.00"),
    )
    order.items = items
    _apply_totals(order)
    db.add(order)
    db.flush()
    return _load(db, order.id)


def update_order(db: Session, order_id: uuid.UUID, data: OrderWrite) -> Order:
    order = _lock(db, order_id)
    if order.status != OrderStatus.draft:
        raise CatalogueError("Only a draft order can be edited", 409)
    items = [_build_item(db, line) for line in data.items]
    order.order_date = data.order_date
    order.notes = data.notes
    order.discount_type = data.discount_type
    order.discount_value = q_value(data.discount_value)
    _replace_items(db, order, items)
    _apply_totals(order)
    db.flush()
    return _load(db, order.id)


def add_item(db: Session, order_id: uuid.UUID, data: OrderItemIn) -> Order:
    order = _lock(db, order_id)
    if order.status != OrderStatus.draft:
        raise CatalogueError("Only a draft order can be edited", 409)
    order.items.append(_build_item(db, data))
    _apply_totals(order)
    db.flush()
    return _load(db, order.id)


def update_item(db: Session, order_id: uuid.UUID, item_id: uuid.UUID, data: OrderItemIn) -> Order:
    order = _lock(db, order_id)
    if order.status != OrderStatus.draft:
        raise CatalogueError("Only a draft order can be edited", 409)
    current = next((item for item in order.items if item.id == item_id), None)
    if current is None:
        raise CatalogueError("Order item not found", 404)
    built = _build_item(db, data)
    current.product_id = built.product_id
    current.product_name_snapshot = built.product_name_snapshot
    current.sku_snapshot = built.sku_snapshot
    current.unit_id = built.unit_id
    current.unit_name_snapshot = built.unit_name_snapshot
    current.quantity = built.quantity
    current.unit_price = built.unit_price
    current.discount_type = built.discount_type
    current.discount_value = built.discount_value
    _apply_totals(order)
    db.flush()
    return _load(db, order.id)


def delete_item(db: Session, order_id: uuid.UUID, item_id: uuid.UUID) -> Order:
    order = _lock(db, order_id)
    if order.status != OrderStatus.draft:
        raise CatalogueError("Only a draft order can be edited", 409)
    current = next((item for item in order.items if item.id == item_id), None)
    if current is None:
        raise CatalogueError("Order item not found", 404)
    order.items.remove(current)
    db.flush()
    _apply_totals(order)
    db.flush()
    return _load(db, order.id)


def get_order(db: Session, order_id: uuid.UUID) -> Order:
    return _load(db, order_id)


def delete_order(db: Session, order_id: uuid.UUID) -> None:
    order = _lock(db, order_id)
    if order.status != OrderStatus.draft:
        raise CatalogueError("Only a draft order can be deleted", 409)
    db.delete(order)
    db.flush()


def confirm_order(db: Session, order_id: uuid.UUID) -> Order:
    order = _load(db, order_id)
    order_inventory.confirm_order(db, order)
    db.expire(order)
    return _load(db, order_id)


def cancel_order(db: Session, order_id: uuid.UUID) -> Order:
    order = _load(db, order_id)
    order_inventory.cancel_order(db, order)
    db.expire(order)
    return _load(db, order_id)


def complete_order(db: Session, order_id: uuid.UUID) -> Order:
    order = _lock(db, order_id)
    if order.status != OrderStatus.confirmed:
        raise CatalogueError("Only a confirmed order can be completed", 409)
    order.status = OrderStatus.completed
    order.completed_at = _now()
    db.flush()
    return _load(db, order.id)


def list_orders(
    db: Session,
    *,
    page: int,
    page_size: int,
    q: str | None,
    status: OrderStatus | None,
    date_from: date | None,
    date_to: date | None,
    sort: str,
    direction: str,
) -> tuple[list[OrderListItem], int]:
    item_count = (
        select(func.count(OrderItem.id)).where(OrderItem.order_id == Order.id).correlate(Order).scalar_subquery()
    )
    stmt = select(Order, item_count)
    if q:
        stmt = stmt.where(Order.order_number.ilike(_like(q.strip()), escape="\\"))
    if status is not None:
        stmt = stmt.where(Order.status == status)
    if date_from is not None:
        stmt = stmt.where(Order.order_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Order.order_date <= date_to)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    column = SORTS.get(sort, Order.order_date)
    ordering = column.desc() if direction == "desc" else column.asc()
    rows = db.execute(stmt.order_by(ordering, Order.order_number.asc()).offset((page - 1) * page_size).limit(page_size)).all()
    return [
        OrderListItem(
            id=order.id,
            order_number=order.order_number,
            status=order.status,
            order_date=order.order_date,
            item_count=count,
            grand_total=order.grand_total,
            created_at=order.created_at,
        )
        for order, count in rows
    ], total
