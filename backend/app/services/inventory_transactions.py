from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import CatalogueError
from app.models.enums import InventoryTransactionStatus, InventoryTransactionType, ProductStatus
from app.models.inventory import InventorySequence, InventoryTransaction, InventoryTransactionItem, StockBalance
from app.models.product import Product
from app.schemas.inventory import (
    TransactionItemIn,
    TransactionItemOut,
    TransactionListItem,
    TransactionOut,
    TransactionUpdate,
    TransactionWrite,
)
from app.services.inventory_valuation import apply_decrease, apply_increase, apply_reversal, q_money, q_qty
from app.services.unit_conversion import to_selling_quantity

INCREASE_TYPES = {
    InventoryTransactionType.opening_stock,
    InventoryTransactionType.stock_receipt,
}
REASON_TYPES = {
    InventoryTransactionType.stock_issue,
    InventoryTransactionType.stock_adjustment,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_transaction(db: Session, transaction_id: uuid.UUID) -> InventoryTransaction:
    transaction = db.scalar(
        select(InventoryTransaction)
        .where(InventoryTransaction.id == transaction_id)
        .options(
            selectinload(InventoryTransaction.items).selectinload(InventoryTransactionItem.product),
            selectinload(InventoryTransaction.items).selectinload(InventoryTransactionItem.unit),
        )
    )
    if transaction is None:
        raise CatalogueError("Transaction not found", 404)
    return transaction


def _lock_transaction(db: Session, transaction_id: uuid.UUID) -> InventoryTransaction:
    transaction = db.scalar(
        select(InventoryTransaction).where(InventoryTransaction.id == transaction_id).with_for_update()
    )
    if transaction is None:
        raise CatalogueError("Transaction not found", 404)
    return transaction


def next_transaction_number(db: Session, on: date) -> str:
    year = on.year
    db.execute(
        pg_insert(InventorySequence).values(year=year, last_number=0).on_conflict_do_nothing(index_elements=["year"])
    )
    row = db.scalar(select(InventorySequence).where(InventorySequence.year == year).with_for_update())
    if row is None:
        raise CatalogueError("Could not allocate a transaction number", 409)
    row.last_number += 1
    db.flush()
    return f"INV-{year}-{row.last_number:06d}"


def _stockable_product(db: Session, product_id: uuid.UUID) -> Product:
    product = db.get(Product, product_id)
    if product is None or product.deleted_at is not None:
        raise CatalogueError("Product not found", 404)
    if product.status != ProductStatus.active:
        raise CatalogueError("Product is not active", 422)
    return product


def _balance_qty(db: Session, product_id: uuid.UUID) -> Decimal:
    balance = db.scalar(select(StockBalance).where(StockBalance.product_id == product_id))
    if balance is None:
        return Decimal("0")
    return balance.quantity_on_hand


def _assert_opening_allowed(db: Session, product: Product) -> None:
    if _balance_qty(db, product.id) > 0:
        raise CatalogueError(f"{product.name} already has stock. Use a receipt.", 422)
    existing = db.scalar(
        select(InventoryTransaction.id)
        .join(InventoryTransactionItem, InventoryTransactionItem.transaction_id == InventoryTransaction.id)
        .where(
            InventoryTransactionItem.product_id == product.id,
            InventoryTransaction.transaction_type == InventoryTransactionType.opening_stock,
            InventoryTransaction.status == InventoryTransactionStatus.posted,
        )
    )
    if existing is not None:
        raise CatalogueError(f"{product.name} already has opening stock. Use a receipt.", 422)


def _require_reason(transaction_type: InventoryTransactionType, reason: str | None) -> None:
    if transaction_type in REASON_TYPES and not reason:
        raise CatalogueError("A reason is required", 422)


def _line_cost(quantity: Decimal, unit_cost: Decimal | None, product_name: str) -> tuple[Decimal, Decimal]:
    if unit_cost is None:
        raise CatalogueError(f"Unit cost is required for {product_name}", 422)
    if unit_cost < 0:
        raise CatalogueError("Unit cost cannot be negative", 422)
    cost = q_money(unit_cost)
    return cost, q_money(quantity * cost)


def _prepare_line(
    db: Session,
    transaction_type: InventoryTransactionType,
    incoming: TransactionItemIn,
    *,
    on_hand: Decimal | None = None,
) -> InventoryTransactionItem:
    product = _stockable_product(db, incoming.product_id)
    current = _balance_qty(db, product.id) if on_hand is None else on_hand
    if transaction_type == InventoryTransactionType.opening_stock:
        _assert_opening_allowed(db, product)
    if transaction_type == InventoryTransactionType.stock_adjustment:
        if incoming.physical_quantity is None:
            raise CatalogueError(f"Enter the physical stock for {product.name}", 422)
        if incoming.physical_quantity < 0:
            raise CatalogueError("Physical stock cannot be negative", 422)
        physical = (
            Decimal("0")
            if incoming.physical_quantity == 0
            else to_selling_quantity(db, product, incoming.unit_id, incoming.physical_quantity)
        )
        delta = q_qty(physical - current)
        if delta == 0:
            raise CatalogueError(f"{product.name} already matches the physical count", 422)
        if delta > 0 and current == 0:
            unit_cost, total_cost = _line_cost(incoming.physical_quantity, incoming.unit_cost, product.name)
        elif delta > 0:
            average = _average(db, product.id)
            unit_cost = q_money(average)
            total_cost = q_money(delta * average)
        else:
            average = _average(db, product.id)
            unit_cost = q_money(average)
            total_cost = q_money(abs(delta) * average)
        return InventoryTransactionItem(
            product_id=product.id,
            unit_id=incoming.unit_id,
            quantity=q_qty(incoming.physical_quantity),
            unit_cost=unit_cost,
            total_cost=total_cost,
            quantity_delta=delta,
        )

    if incoming.quantity is None or incoming.quantity <= 0:
        raise CatalogueError("Quantity must be greater than zero", 422)
    stock_qty = to_selling_quantity(db, product, incoming.unit_id, incoming.quantity)
    if stock_qty <= 0:
        raise CatalogueError("Quantity must be greater than zero", 422)
    if transaction_type == InventoryTransactionType.stock_issue:
        average = _average(db, product.id)
        delta = -stock_qty
        unit_cost = q_money(average)
        total_cost = q_money(stock_qty * average)
    elif transaction_type in INCREASE_TYPES:
        unit_cost, total_cost = _line_cost(incoming.quantity, incoming.unit_cost, product.name)
        delta = stock_qty
    else:
        raise CatalogueError("This transaction type cannot be created directly", 422)
    return InventoryTransactionItem(
        product_id=product.id,
        unit_id=incoming.unit_id,
        quantity=q_qty(incoming.quantity),
        unit_cost=unit_cost,
        total_cost=total_cost,
        quantity_delta=delta,
    )


def _average(db: Session, product_id: uuid.UUID) -> Decimal:
    balance = db.scalar(select(StockBalance).where(StockBalance.product_id == product_id))
    if balance is None:
        return Decimal("0")
    return balance.average_cost


def _prepare_items(
    db: Session,
    transaction_type: InventoryTransactionType,
    items: list[TransactionItemIn],
) -> list[InventoryTransactionItem]:
    seen: set[uuid.UUID] = set()
    prepared: list[InventoryTransactionItem] = []
    for incoming in items:
        if incoming.product_id in seen:
            raise CatalogueError("Duplicate product on this transaction", 422)
        seen.add(incoming.product_id)
        prepared.append(_prepare_line(db, transaction_type, incoming))
    return prepared


def _replace_items(db: Session, transaction: InventoryTransaction, items: list[InventoryTransactionItem]) -> None:
    transaction.items.clear()
    db.flush()
    for item in items:
        item.transaction_id = transaction.id
        transaction.items.append(item)
    db.flush()


def create_transaction(db: Session, data: TransactionWrite) -> InventoryTransaction:
    if data.transaction_type == InventoryTransactionType.reversal:
        raise CatalogueError("Reversals are created from a posted transaction", 422)
    _require_reason(data.transaction_type, data.reason)
    prepared = _prepare_items(db, data.transaction_type, data.items)
    transaction = InventoryTransaction(
        transaction_number=next_transaction_number(db, data.transaction_date),
        transaction_type=data.transaction_type,
        status=InventoryTransactionStatus.draft,
        reference_number=data.reference_number,
        reference_type=data.reference_type,
        reference_id=data.reference_id,
        transaction_date=data.transaction_date,
        notes=data.notes,
        reason=data.reason,
        created_by=None,
    )
    db.add(transaction)
    db.flush()
    _replace_items(db, transaction, prepared)
    if data.post:
        return post_transaction(db, transaction.id)
    return _load_transaction(db, transaction.id)


def update_transaction(db: Session, transaction_id: uuid.UUID, data: TransactionUpdate) -> InventoryTransaction:
    transaction = _lock_transaction(db, transaction_id)
    if transaction.status != InventoryTransactionStatus.draft:
        raise CatalogueError("Only a draft transaction can be edited", 409)
    _require_reason(transaction.transaction_type, data.reason)
    prepared = _prepare_items(db, transaction.transaction_type, data.items)
    transaction.transaction_date = data.transaction_date
    transaction.reference_number = data.reference_number
    transaction.reference_type = data.reference_type
    transaction.reference_id = data.reference_id
    transaction.notes = data.notes
    transaction.reason = data.reason
    db.flush()
    loaded = _load_transaction(db, transaction.id)
    _replace_items(db, loaded, prepared)
    return _load_transaction(db, transaction.id)


def delete_transaction(db: Session, transaction_id: uuid.UUID) -> None:
    transaction = _lock_transaction(db, transaction_id)
    if transaction.status != InventoryTransactionStatus.draft:
        raise CatalogueError("Only a draft transaction can be deleted", 409)
    db.delete(transaction)
    db.flush()


def _lock_balance(db: Session, product_id: uuid.UUID) -> StockBalance:
    db.execute(
        pg_insert(StockBalance)
        .values(
            id=uuid.uuid4(),
            product_id=product_id,
            quantity_on_hand=Decimal("0"),
            average_cost=Decimal("0"),
            inventory_value=Decimal("0"),
        )
        .on_conflict_do_nothing(index_elements=["product_id"])
    )
    balance = db.scalar(select(StockBalance).where(StockBalance.product_id == product_id).with_for_update())
    if balance is None:
        raise CatalogueError("Could not lock the stock balance", 409)
    return balance


def post_transaction(db: Session, transaction_id: uuid.UUID) -> InventoryTransaction:
    transaction = _lock_transaction(db, transaction_id)
    if transaction.status == InventoryTransactionStatus.posted:
        raise CatalogueError("This transaction is already posted", 409)
    if transaction.status != InventoryTransactionStatus.draft:
        raise CatalogueError("Only a draft transaction can be posted", 409)
    if transaction.transaction_type == InventoryTransactionType.reversal:
        raise CatalogueError("Reversals are posted when they are created", 422)
    loaded = _load_transaction(db, transaction.id)
    if not loaded.items:
        raise CatalogueError("Add at least one product", 422)
    _require_reason(loaded.transaction_type, loaded.reason)
    staged: list[tuple[InventoryTransactionItem, Product]] = []
    for item in loaded.items:
        product = _stockable_product(db, item.product_id)
        if loaded.transaction_type == InventoryTransactionType.opening_stock:
            _assert_opening_allowed(db, product)
        _ensure_line_unit(db, loaded.transaction_type, item, product)
        staged.append((item, product))
    balances = {
        product_id: _lock_balance(db, product_id)
        for product_id in sorted({item.product_id for item, _ in staged})
    }
    for item, product in staged:
        _ensure_available(db, loaded.transaction_type, item, product, balances[item.product_id])
    for item, product in staged:
        _apply_item(db, loaded.transaction_type, item, product, balances[item.product_id])
    loaded.status = InventoryTransactionStatus.posted
    loaded.posted_at = _now()
    db.flush()
    return _load_transaction(db, loaded.id)


def _ensure_line_unit(
    db: Session,
    transaction_type: InventoryTransactionType,
    item: InventoryTransactionItem,
    product: Product,
) -> None:
    if transaction_type == InventoryTransactionType.stock_adjustment:
        if item.quantity > 0:
            to_selling_quantity(db, product, item.unit_id, item.quantity)
        return
    if item.quantity <= 0:
        raise CatalogueError("Quantity must be greater than zero", 422)
    to_selling_quantity(db, product, item.unit_id, item.quantity)


def _ensure_available(
    db: Session,
    transaction_type: InventoryTransactionType,
    item: InventoryTransactionItem,
    product: Product,
    balance: StockBalance,
) -> None:
    if transaction_type == InventoryTransactionType.stock_issue:
        needed = to_selling_quantity(db, product, item.unit_id, item.quantity)
        if balance.quantity_on_hand < needed:
            raise CatalogueError(f"Insufficient stock for {product.name}", 422)
        return
    if transaction_type == InventoryTransactionType.opening_stock and balance.quantity_on_hand > 0:
        raise CatalogueError(f"{product.name} already has stock. Use a receipt.", 422)


def _apply_item(
    db: Session,
    transaction_type: InventoryTransactionType,
    item: InventoryTransactionItem,
    product: Product,
    balance: StockBalance,
) -> None:
    if transaction_type == InventoryTransactionType.stock_adjustment:
        physical = (
            Decimal("0")
            if item.quantity == 0
            else to_selling_quantity(db, product, item.unit_id, item.quantity)
        )
        delta = q_qty(physical - balance.quantity_on_hand)
        if delta == 0:
            raise CatalogueError(f"{product.name} already matches the physical count", 422)
        if delta > 0:
            if balance.quantity_on_hand == 0:
                if item.unit_cost < 0:
                    raise CatalogueError("Unit cost cannot be negative", 422)
                total = q_money(item.quantity * item.unit_cost)
            else:
                total = q_money(delta * balance.average_cost)
                item.unit_cost = q_money(balance.average_cost)
            apply_increase(balance, delta, total)
            item.total_cost = total
        else:
            total, unit_cost = apply_decrease(balance, abs(delta))
            item.unit_cost = unit_cost
            item.total_cost = total
        item.quantity_delta = delta
        return

    stock_qty = to_selling_quantity(db, product, item.unit_id, item.quantity)
    if transaction_type == InventoryTransactionType.stock_issue:
        total, unit_cost = apply_decrease(balance, stock_qty)
        item.unit_cost = unit_cost
        item.total_cost = total
        item.quantity_delta = -stock_qty
        return
    if transaction_type in INCREASE_TYPES:
        total = q_money(item.quantity * item.unit_cost)
        apply_increase(balance, stock_qty, total)
        item.total_cost = total
        item.quantity_delta = stock_qty
        return
    raise CatalogueError("This transaction type cannot be posted", 422)


def reverse_transaction(db: Session, transaction_id: uuid.UUID) -> InventoryTransaction:
    original = _lock_transaction(db, transaction_id)
    if original.transaction_type == InventoryTransactionType.reversal:
        raise CatalogueError("A reversal cannot be reversed", 422)
    if original.status == InventoryTransactionStatus.reversed:
        raise CatalogueError("This transaction is already reversed", 409)
    if original.status != InventoryTransactionStatus.posted:
        raise CatalogueError("Only a posted transaction can be reversed", 409)
    loaded = _load_transaction(db, original.id)
    product_ids = sorted({item.product_id for item in loaded.items})
    balances = {product_id: _lock_balance(db, product_id) for product_id in product_ids}
    for item in loaded.items:
        projected = q_qty(balances[item.product_id].quantity_on_hand - item.quantity_delta)
        if projected < 0:
            raise CatalogueError("Reversal would make stock negative", 422)
    reversal = InventoryTransaction(
        transaction_number=next_transaction_number(db, date.today()),
        transaction_type=InventoryTransactionType.reversal,
        status=InventoryTransactionStatus.posted,
        reference_number=original.transaction_number,
        reference_type="inventory_transaction",
        reference_id=original.id,
        transaction_date=date.today(),
        notes=f"Reversal of {original.transaction_number}",
        reason=original.reason,
        created_by=None,
        posted_at=_now(),
        reversal_of_id=original.id,
    )
    db.add(reversal)
    db.flush()
    for item in loaded.items:
        balance = balances[item.product_id]
        apply_reversal(balance, item.quantity_delta, item.total_cost)
        db.add(
            InventoryTransactionItem(
                transaction_id=reversal.id,
                product_id=item.product_id,
                unit_id=item.unit_id,
                quantity=item.quantity,
                unit_cost=item.unit_cost,
                total_cost=item.total_cost,
                quantity_delta=-item.quantity_delta,
            )
        )
    original.status = InventoryTransactionStatus.reversed
    original.reversed_at = _now()
    db.flush()
    return _load_transaction(db, reversal.id)


def get_transaction(db: Session, transaction_id: uuid.UUID) -> InventoryTransaction:
    return _load_transaction(db, transaction_id)


def list_transactions(
    db: Session,
    *,
    page: int,
    page_size: int,
    transaction_type: InventoryTransactionType | None,
    status: InventoryTransactionStatus | None,
    date_from: date | None,
    date_to: date | None,
    product_id: uuid.UUID | None,
    q: str | None,
) -> tuple[list[TransactionListItem], int]:
    item_count = func.count(InventoryTransactionItem.id)
    total_quantity = func.coalesce(func.sum(func.abs(InventoryTransactionItem.quantity_delta)), 0)
    total_value = func.coalesce(func.sum(InventoryTransactionItem.total_cost), 0)
    stmt = (
        select(InventoryTransaction, item_count, total_quantity, total_value)
        .outerjoin(InventoryTransactionItem, InventoryTransactionItem.transaction_id == InventoryTransaction.id)
        .group_by(InventoryTransaction.id)
    )
    if transaction_type is not None:
        stmt = stmt.where(InventoryTransaction.transaction_type == transaction_type)
    if status is not None:
        stmt = stmt.where(InventoryTransaction.status == status)
    if date_from is not None:
        stmt = stmt.where(InventoryTransaction.transaction_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(InventoryTransaction.transaction_date <= date_to)
    if product_id is not None:
        stmt = stmt.where(
            InventoryTransaction.id.in_(
                select(InventoryTransactionItem.transaction_id).where(InventoryTransactionItem.product_id == product_id)
            )
        )
    if q:
        pattern = f"%{q.strip()}%"
        product_match = InventoryTransaction.id.in_(
            select(InventoryTransactionItem.transaction_id)
            .join(Product, Product.id == InventoryTransactionItem.product_id)
            .where(or_(Product.name.ilike(pattern), Product.sku.ilike(pattern)))
        )
        stmt = stmt.where(
            or_(
                InventoryTransaction.transaction_number.ilike(pattern),
                InventoryTransaction.reference_number.ilike(pattern),
                product_match,
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.execute(
        stmt.order_by(InventoryTransaction.transaction_date.desc(), InventoryTransaction.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [
        TransactionListItem(
            id=transaction.id,
            transaction_number=transaction.transaction_number,
            transaction_type=transaction.transaction_type,
            status=transaction.status,
            transaction_date=transaction.transaction_date,
            reference_number=transaction.reference_number,
            item_count=count,
            total_quantity=quantity,
            total_value=value,
        )
        for transaction, count, quantity, value in rows
    ]
    return items, total


def to_transaction_out(transaction: InventoryTransaction) -> TransactionOut:
    items = [
        TransactionItemOut(
            id=item.id,
            product_id=item.product_id,
            product_name=item.product.name,
            sku=item.product.sku,
            unit_id=item.unit_id,
            unit_symbol=item.unit.symbol,
            quantity=item.quantity,
            unit_cost=item.unit_cost,
            total_cost=item.total_cost,
            quantity_delta=item.quantity_delta,
        )
        for item in transaction.items
    ]
    total_quantity = sum((abs(item.quantity_delta) for item in transaction.items), Decimal("0"))
    total_value = sum((item.total_cost for item in transaction.items), Decimal("0"))
    return TransactionOut(
        id=transaction.id,
        transaction_number=transaction.transaction_number,
        transaction_type=transaction.transaction_type,
        status=transaction.status,
        reference_number=transaction.reference_number,
        reference_type=transaction.reference_type,
        reference_id=transaction.reference_id,
        transaction_date=transaction.transaction_date,
        notes=transaction.notes,
        reason=transaction.reason,
        created_by=transaction.created_by,
        created_at=transaction.created_at,
        posted_at=transaction.posted_at,
        reversed_at=transaction.reversed_at,
        reversal_of_id=transaction.reversal_of_id,
        item_count=len(items),
        total_quantity=total_quantity,
        total_value=total_value,
        items=items,
    )
