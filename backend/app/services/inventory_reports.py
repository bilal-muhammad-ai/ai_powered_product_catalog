from __future__ import annotations

import csv
import io
import uuid
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.enums import InventoryTransactionStatus, StockStatus
from app.models.inventory import InventoryTransaction, InventoryTransactionItem, StockBalance
from app.models.product import Product
from app.models.unit import Unit
from app.services.inventory import list_balances


def _csv(header: list[str], rows: list[list[object]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    for row in rows:
        writer.writerow(["" if value is None else value for value in row])
    return buffer.getvalue()


def stock_summary(
    db: Session,
    *,
    q: str | None,
    category_id: uuid.UUID | None,
    status: StockStatus | None,
) -> tuple[list[str], list[list[object]]]:
    items, _total = list_balances(
        db,
        page=1,
        page_size=5000,
        q=q,
        category_id=category_id,
        brand_option_id=None,
        brand=None,
        status=status,
        sort="name",
        direction="asc",
    )
    header = ["Product", "SKU", "Category", "Quantity", "Unit", "Average cost", "Inventory value", "Status"]
    rows = [
        [
            item.product_name,
            item.sku,
            item.category_name,
            item.quantity_on_hand,
            item.unit_symbol,
            item.average_cost,
            item.inventory_value,
            item.stock_status.value,
        ]
        for item in items
    ]
    return header, rows


def valuation_report(db: Session, *, q: str | None) -> tuple[list[str], list[list[object]]]:
    header, rows = stock_summary(db, q=q, category_id=None, status=None)
    keep = [0, 1, 3, 5, 6]
    titles = ["Product", "SKU", "Quantity", "Average cost", "Total value"]
    return titles, [[row[index] for index in keep] for row in rows]


def low_stock_report(db: Session) -> tuple[list[str], list[list[object]]]:
    items, _total = list_balances(
        db,
        page=1,
        page_size=5000,
        q=None,
        category_id=None,
        brand_option_id=None,
        brand=None,
        status=StockStatus.low_stock,
        sort="quantity",
        direction="asc",
    )
    header = ["Product", "SKU", "Current quantity", "Minimum stock", "Difference", "Unit"]
    rows = []
    for item in items:
        minimum = item.minimum_stock_level or 0
        rows.append(
            [
                item.product_name,
                item.sku,
                item.quantity_on_hand,
                minimum,
                item.quantity_on_hand - minimum,
                item.unit_symbol,
            ]
        )
    return header, rows


def out_of_stock_report(db: Session) -> tuple[list[str], list[list[object]]]:
    items, _total = list_balances(
        db,
        page=1,
        page_size=5000,
        q=None,
        category_id=None,
        brand_option_id=None,
        brand=None,
        status=StockStatus.out_of_stock,
        sort="name",
        direction="asc",
    )
    header = ["Product", "SKU", "Category", "Quantity", "Unit"]
    rows = [
        [item.product_name, item.sku, item.category_name, item.quantity_on_hand, item.unit_symbol] for item in items
    ]
    return header, rows


def movement_report(
    db: Session,
    *,
    date_from: date | None,
    date_to: date | None,
    q: str | None,
) -> tuple[list[str], list[list[object]]]:
    stmt = (
        select(InventoryTransaction, InventoryTransactionItem, Product, Unit.symbol)
        .join(InventoryTransactionItem, InventoryTransactionItem.transaction_id == InventoryTransaction.id)
        .join(Product, Product.id == InventoryTransactionItem.product_id)
        .join(Unit, Unit.id == InventoryTransactionItem.unit_id)
        .where(
            InventoryTransaction.status.in_(
                (InventoryTransactionStatus.posted, InventoryTransactionStatus.reversed)
            )
        )
        .order_by(InventoryTransaction.transaction_date.desc(), InventoryTransaction.transaction_number.desc())
    )
    if date_from is not None:
        stmt = stmt.where(InventoryTransaction.transaction_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(InventoryTransaction.transaction_date <= date_to)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Product.name.ilike(pattern),
                Product.sku.ilike(pattern),
                InventoryTransaction.transaction_number.ilike(pattern),
            )
        )
    header = [
        "Transaction number",
        "Date",
        "Product",
        "SKU",
        "Type",
        "Quantity in",
        "Quantity out",
        "Unit",
        "Cost",
        "Reference",
    ]
    rows: list[list[object]] = []
    for transaction, item, product, symbol in db.execute(stmt).all():
        inbound = item.quantity_delta if item.quantity_delta > 0 else 0
        outbound = abs(item.quantity_delta) if item.quantity_delta < 0 else 0
        rows.append(
            [
                transaction.transaction_number,
                transaction.transaction_date.isoformat(),
                product.name,
                product.sku,
                transaction.transaction_type.value,
                inbound,
                outbound,
                symbol,
                item.total_cost,
                transaction.reference_number or "",
            ]
        )
    return header, rows


def render_csv(header: list[str], rows: list[list[object]]) -> str:
    return _csv(header, rows)


def category_value_total(db: Session) -> list[tuple[str, object]]:
    return db.execute(
        select(Category.name, func.coalesce(func.sum(StockBalance.inventory_value), 0))
        .join(Product, Product.category_id == Category.id)
        .join(StockBalance, StockBalance.product_id == Product.id)
        .group_by(Category.name)
    ).all()
