from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import CatalogueError
from app.models.attribute import AttributeOption, CategoryAttribute
from app.models.category import Category
from app.models.enums import InventoryTransactionStatus, ProductStatus, StockStatus
from app.models.inventory import (
    InventoryTransaction,
    InventoryTransactionItem,
    ProductStockSettings,
    StockBalance,
)
from app.models.product import Product, ProductAttributeValue
from app.models.unit import Unit
from app.schemas.inventory import (
    BalanceItem,
    CatalogHit,
    CategoryValue,
    InventoryDetail,
    InventorySummary,
    MovementOut,
    StockSettingsIn,
    StockSettingsOut,
    TypeCount,
)
from app.services.category_lookup import get_category
from app.services.inventory_transactions import list_transactions
from app.services.inventory_valuation import q_qty

SORTS = {
    "name": Product.name,
    "sku": Product.sku,
    "quantity": StockBalance.quantity_on_hand,
    "average_cost": StockBalance.average_cost,
    "value": StockBalance.inventory_value,
}


def stock_status(quantity: Decimal, minimum: Decimal | None) -> StockStatus:
    if quantity <= 0:
        return StockStatus.out_of_stock
    if minimum is not None and quantity <= minimum:
        return StockStatus.low_stock
    return StockStatus.in_stock


def _brand_name():
    return (
        select(AttributeOption.label)
        .join(ProductAttributeValue, ProductAttributeValue.option_id == AttributeOption.id)
        .join(CategoryAttribute, CategoryAttribute.id == ProductAttributeValue.attribute_id)
        .where(
            ProductAttributeValue.product_id == Product.id,
            CategoryAttribute.code == "brand",
        )
        .limit(1)
        .scalar_subquery()
    )


def _like(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _balance_stmt():
    brand = _brand_name()
    return (
        select(
            Product,
            Category.name,
            Unit.symbol,
            StockBalance,
            ProductStockSettings,
            brand.label("brand"),
        )
        .join(StockBalance, StockBalance.product_id == Product.id)
        .join(Category, Category.id == Product.category_id)
        .join(Unit, Unit.id == Product.selling_unit_id)
        .outerjoin(ProductStockSettings, ProductStockSettings.product_id == Product.id)
    )


def _to_balance(
    product: Product,
    category_name: str,
    unit_symbol: str,
    balance: StockBalance,
    settings: ProductStockSettings | None,
    brand: str | None,
) -> BalanceItem:
    minimum = settings.minimum_stock_level if settings is not None else None
    return BalanceItem(
        product_id=product.id,
        product_name=product.name,
        sku=product.sku,
        category_id=product.category_id,
        category_name=category_name,
        brand=brand,
        quantity_on_hand=balance.quantity_on_hand,
        unit_id=product.selling_unit_id,
        unit_symbol=unit_symbol,
        average_cost=balance.average_cost,
        inventory_value=balance.inventory_value,
        minimum_stock_level=minimum,
        reorder_level=settings.reorder_level if settings is not None else None,
        maximum_stock_level=settings.maximum_stock_level if settings is not None else None,
        stock_status=stock_status(balance.quantity_on_hand, minimum),
    )


def _apply_filters(
    stmt,
    *,
    q: str | None,
    category_id: uuid.UUID | None,
    brand_option_id: uuid.UUID | None,
    brand: str | None,
    status: StockStatus | None,
    db: Session,
):
    if q:
        pattern = _like(q.strip())
        stmt = stmt.where(
            or_(
                Product.name.ilike(pattern, escape="\\"),
                Product.sku.ilike(pattern, escape="\\"),
                Product.code.ilike(pattern, escape="\\"),
            )
        )
    if category_id is not None:
        category = get_category(db, category_id)
        stmt = stmt.where(Category.path.startswith(category.path))
    if brand_option_id is not None:
        stmt = stmt.where(
            Product.id.in_(
                select(ProductAttributeValue.product_id)
                .join(CategoryAttribute, CategoryAttribute.id == ProductAttributeValue.attribute_id)
                .where(
                    CategoryAttribute.code == "brand",
                    ProductAttributeValue.option_id == brand_option_id,
                )
            )
        )
    if brand:
        pattern = _like(brand.strip())
        stmt = stmt.where(
            Product.id.in_(
                select(ProductAttributeValue.product_id)
                .join(CategoryAttribute, CategoryAttribute.id == ProductAttributeValue.attribute_id)
                .join(AttributeOption, AttributeOption.id == ProductAttributeValue.option_id)
                .where(CategoryAttribute.code == "brand", AttributeOption.label.ilike(pattern, escape="\\"))
            )
        )
    if status == StockStatus.out_of_stock:
        stmt = stmt.where(StockBalance.quantity_on_hand <= 0)
    elif status == StockStatus.low_stock:
        stmt = stmt.where(
            and_(
                StockBalance.quantity_on_hand > 0,
                ProductStockSettings.minimum_stock_level.is_not(None),
                StockBalance.quantity_on_hand <= ProductStockSettings.minimum_stock_level,
            )
        )
    elif status == StockStatus.in_stock:
        stmt = stmt.where(
            and_(
                StockBalance.quantity_on_hand > 0,
                or_(
                    ProductStockSettings.minimum_stock_level.is_(None),
                    StockBalance.quantity_on_hand > ProductStockSettings.minimum_stock_level,
                ),
            )
        )
    return stmt


def list_balances(
    db: Session,
    *,
    page: int,
    page_size: int,
    q: str | None,
    category_id: uuid.UUID | None,
    brand_option_id: uuid.UUID | None,
    brand: str | None,
    status: StockStatus | None,
    sort: str,
    direction: str,
) -> tuple[list[BalanceItem], int]:
    column = SORTS.get(sort, Product.name)
    stmt = _apply_filters(
        _balance_stmt(),
        q=q,
        category_id=category_id,
        brand_option_id=brand_option_id,
        brand=brand,
        status=status,
        db=db,
    )
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    ordering = column.desc() if direction == "desc" else column.asc()
    rows = db.execute(stmt.order_by(ordering, Product.name.asc()).offset((page - 1) * page_size).limit(page_size)).all()
    return [_to_balance(*row) for row in rows], total


def get_balance(db: Session, product_id: uuid.UUID) -> InventoryDetail:
    product = db.get(Product, product_id)
    if product is None or product.deleted_at is not None:
        raise CatalogueError("Product not found", 404)
    row = db.execute(_balance_stmt().where(Product.id == product_id)).first()
    category = db.get(Category, product.category_id)
    unit = db.get(Unit, product.selling_unit_id)
    net_symbol = None
    if product.net_quantity_unit_id is not None:
        net_unit = db.get(Unit, product.net_quantity_unit_id)
        net_symbol = net_unit.symbol if net_unit is not None else None
    brand_name = db.scalar(
        select(AttributeOption.label)
        .join(ProductAttributeValue, ProductAttributeValue.option_id == AttributeOption.id)
        .join(CategoryAttribute, CategoryAttribute.id == ProductAttributeValue.attribute_id)
        .where(ProductAttributeValue.product_id == product.id, CategoryAttribute.code == "brand")
        .limit(1)
    )
    if row is None:
        item = BalanceItem(
            product_id=product.id,
            product_name=product.name,
            sku=product.sku,
            category_id=product.category_id,
            category_name=category.name if category is not None else "",
            brand=brand_name,
            quantity_on_hand=Decimal("0"),
            unit_id=product.selling_unit_id,
            unit_symbol=unit.symbol if unit is not None else "",
            average_cost=Decimal("0"),
            inventory_value=Decimal("0"),
            minimum_stock_level=None,
            stock_status=StockStatus.out_of_stock,
        )
    else:
        item = _to_balance(*row)
    return InventoryDetail(
        **item.model_dump(),
        cost_price=product.cost_price,
        currency_code=product.currency_code,
        barcode=product.barcode,
        net_quantity=product.net_quantity,
        net_quantity_unit_symbol=net_symbol,
    )


def product_history(
    db: Session,
    product_id: uuid.UUID,
    *,
    transaction_type: str | None = None,
) -> list[MovementOut]:
    if db.get(Product, product_id) is None:
        raise CatalogueError("Product not found", 404)
    stmt = (
        select(InventoryTransaction, InventoryTransactionItem, Unit.symbol)
        .join(InventoryTransactionItem, InventoryTransactionItem.transaction_id == InventoryTransaction.id)
        .join(Unit, Unit.id == InventoryTransactionItem.unit_id)
        .where(
            InventoryTransactionItem.product_id == product_id,
            InventoryTransaction.status.in_(
                (InventoryTransactionStatus.posted, InventoryTransactionStatus.reversed)
            ),
        )
        .order_by(InventoryTransaction.transaction_date.desc(), InventoryTransaction.posted_at.desc())
    )
    if transaction_type:
        stmt = stmt.where(InventoryTransaction.transaction_type == transaction_type)
    rows = db.execute(stmt).all()
    return [
        MovementOut(
            transaction_id=transaction.id,
            transaction_number=transaction.transaction_number,
            transaction_type=transaction.transaction_type,
            status=transaction.status,
            transaction_date=transaction.transaction_date,
            quantity=item.quantity,
            quantity_delta=item.quantity_delta,
            unit_symbol=symbol,
            unit_cost=item.unit_cost,
            total_cost=item.total_cost,
            reference_number=transaction.reference_number,
        )
        for transaction, item, symbol in rows
    ]


def _counts(db: Session) -> tuple[int, int]:
    low = db.scalar(
        select(func.count())
        .select_from(StockBalance)
        .outerjoin(ProductStockSettings, ProductStockSettings.product_id == StockBalance.product_id)
        .where(
            StockBalance.quantity_on_hand > 0,
            ProductStockSettings.minimum_stock_level.is_not(None),
            StockBalance.quantity_on_hand <= ProductStockSettings.minimum_stock_level,
        )
    ) or 0
    out = db.scalar(select(func.count()).select_from(StockBalance).where(StockBalance.quantity_on_hand <= 0)) or 0
    return low, out


def summary(db: Session) -> InventorySummary:
    product_count = db.scalar(select(func.count()).select_from(StockBalance).where(StockBalance.quantity_on_hand > 0)) or 0
    total_quantity = db.scalar(select(func.coalesce(func.sum(StockBalance.quantity_on_hand), 0))) or 0
    total_value = db.scalar(select(func.coalesce(func.sum(StockBalance.inventory_value), 0))) or 0
    low_count, out_count = _counts(db)
    recent, _total = list_transactions(
        db,
        page=1,
        page_size=8,
        transaction_type=None,
        status=None,
        date_from=None,
        date_to=None,
        product_id=None,
        q=None,
    )
    low_rows, _low_total = list_balances(
        db,
        page=1,
        page_size=5,
        q=None,
        category_id=None,
        brand_option_id=None,
        brand=None,
        status=StockStatus.low_stock,
        sort="quantity",
        direction="asc",
    )
    out_rows, _out_total = list_balances(
        db,
        page=1,
        page_size=5,
        q=None,
        category_id=None,
        brand_option_id=None,
        brand=None,
        status=StockStatus.out_of_stock,
        sort="name",
        direction="asc",
    )
    category_rows = db.execute(
        select(Category.name, func.coalesce(func.sum(StockBalance.inventory_value), 0))
        .join(Product, Product.category_id == Category.id)
        .join(StockBalance, StockBalance.product_id == Product.id)
        .group_by(Category.name)
        .order_by(func.sum(StockBalance.inventory_value).desc())
    ).all()
    type_rows = db.execute(
        select(InventoryTransaction.transaction_type, func.count())
        .where(InventoryTransaction.status.in_((InventoryTransactionStatus.posted, InventoryTransactionStatus.reversed)))
        .group_by(InventoryTransaction.transaction_type)
    ).all()
    return InventorySummary(
        product_count=product_count,
        total_quantity=total_quantity,
        total_value=total_value,
        low_stock_count=low_count,
        out_of_stock_count=out_count,
        recent_transactions=recent,
        low_stock=low_rows,
        out_of_stock=out_rows,
        value_by_category=[CategoryValue(category_name=name, inventory_value=value) for name, value in category_rows],
        movement_counts=[TypeCount(transaction_type=txn_type, count=count) for txn_type, count in type_rows],
    )


def search_catalog(db: Session, q: str | None, limit: int = 20) -> list[CatalogHit]:
    brand = _brand_name()
    stmt = (
        select(Product, Category.name, Unit.symbol, StockBalance, brand.label("brand"))
        .join(Category, Category.id == Product.category_id)
        .join(Unit, Unit.id == Product.selling_unit_id)
        .outerjoin(StockBalance, StockBalance.product_id == Product.id)
        .where(Product.deleted_at.is_(None), Product.status == ProductStatus.active)
        .order_by(Product.name.asc())
        .limit(limit)
    )
    if q:
        pattern = _like(q.strip())
        stmt = stmt.where(
            or_(
                Product.name.ilike(pattern, escape="\\"),
                Product.sku.ilike(pattern, escape="\\"),
                Product.code.ilike(pattern, escape="\\"),
            )
        )
    rows = db.execute(stmt).all()
    hits: list[CatalogHit] = []
    for product, category_name, symbol, balance, brand_name in rows:
        hits.append(
            CatalogHit(
                product_id=product.id,
                name=product.name,
                sku=product.sku,
                category_name=category_name,
                brand=brand_name,
                unit_id=product.selling_unit_id,
                unit_symbol=symbol,
                quantity_on_hand=balance.quantity_on_hand if balance is not None else Decimal("0"),
                average_cost=balance.average_cost if balance is not None else Decimal("0"),
                net_quantity=product.net_quantity,
                net_quantity_unit_id=product.net_quantity_unit_id,
            )
        )
    return hits


def save_settings(db: Session, product_id: uuid.UUID, data: StockSettingsIn) -> StockSettingsOut:
    product = db.get(Product, product_id)
    if product is None or product.deleted_at is not None:
        raise CatalogueError("Product not found", 404)
    values = {
        "minimum_stock_level": _optional_qty(data.minimum_stock_level, "Minimum stock"),
        "reorder_level": _optional_qty(data.reorder_level, "Reorder level"),
        "maximum_stock_level": _optional_qty(data.maximum_stock_level, "Maximum stock"),
    }
    minimum = values["minimum_stock_level"]
    maximum = values["maximum_stock_level"]
    if minimum is not None and maximum is not None and maximum < minimum:
        raise CatalogueError("Maximum stock cannot be below the minimum", 422)
    if values["reorder_level"] is None:
        values["reorder_level"] = minimum
    settings = db.scalar(select(ProductStockSettings).where(ProductStockSettings.product_id == product_id))
    if settings is None:
        settings = ProductStockSettings(product_id=product_id, **values)
        db.add(settings)
    else:
        for field_name, value in values.items():
            setattr(settings, field_name, value)
    db.flush()
    return StockSettingsOut(product_id=product_id, **values)


def _optional_qty(value: Decimal | None, label: str) -> Decimal | None:
    if value is None:
        return None
    if value < 0:
        raise CatalogueError(f"{label} cannot be negative", 422)
    return q_qty(value)
