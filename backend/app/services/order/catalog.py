import uuid
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased

from app.models.category import Category
from app.models.enums import ProductStatus
from app.models.inventory import StockBalance
from app.models.product import Product
from app.models.unit import Unit
from app.schemas.order.order import OrderCatalogHit
from app.services.category_lookup import get_category


def _like(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def search_catalog(
    db: Session,
    *,
    q: str | None,
    category_id: uuid.UUID | None,
    limit: int = 20,
) -> list[OrderCatalogHit]:
    text = (q or "").strip()
    if len(text) < 2 and category_id is None:
        return []
    quantity_unit = aliased(Unit)
    stmt = (
        select(Product, Category.name, Unit.symbol, quantity_unit.symbol, StockBalance)
        .join(Category, Category.id == Product.category_id)
        .join(Unit, Unit.id == Product.selling_unit_id)
        .outerjoin(quantity_unit, quantity_unit.id == Product.net_quantity_unit_id)
        .outerjoin(StockBalance, StockBalance.product_id == Product.id)
        .where(Product.deleted_at.is_(None), Product.status == ProductStatus.active)
        .order_by(Product.name.asc())
        .limit(limit)
    )
    if len(text) >= 2:
        pattern = _like(text)
        stmt = stmt.where(
            or_(
                Product.name.ilike(pattern, escape="\\"),
                Product.sku.ilike(pattern, escape="\\"),
                Category.name.ilike(pattern, escape="\\"),
            )
        )
    if category_id is not None:
        category = get_category(db, category_id)
        stmt = stmt.where(Category.path.startswith(category.path))
    hits: list[OrderCatalogHit] = []
    for product, category_name, symbol, quantity_symbol, balance in db.execute(stmt).all():
        hits.append(
            OrderCatalogHit(
                product_id=product.id,
                name=product.name,
                sku=product.sku,
                category_id=product.category_id,
                category_name=category_name,
                unit_id=product.selling_unit_id,
                unit_symbol=symbol,
                selling_price=product.selling_price,
                quantity_on_hand=balance.quantity_on_hand if balance is not None else Decimal("0"),
                quantity_unit_id=product.net_quantity_unit_id,
                quantity_unit_symbol=quantity_symbol,
                quantity_unit_price=product.quantity_unit_price,
                net_quantity=product.net_quantity,
            )
        )
    return hits
