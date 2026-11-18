import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import CatalogueError
from app.models.attribute import CategoryAttribute
from app.models.product import Product
from app.models.unit import Unit
from app.schemas.unit import UnitCreate, UnitUpdate


def list_units(db: Session, *, q: str | None, include_inactive: bool) -> list[Unit]:
    stmt = select(Unit).order_by(Unit.name)
    if not include_inactive:
        stmt = stmt.where(Unit.is_active.is_(True))
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(or_(Unit.name.ilike(pattern), Unit.symbol.ilike(pattern)))
    return list(db.scalars(stmt))


def get_unit(db: Session, unit_id: uuid.UUID) -> Unit:
    unit = db.get(Unit, unit_id)
    if unit is None:
        raise CatalogueError("Unit not found", 404)
    return unit


def create_unit(db: Session, data: UnitCreate) -> Unit:
    symbol = data.symbol.strip()
    existing = db.scalar(select(Unit).where(Unit.symbol == symbol))
    if existing is not None:
        raise CatalogueError("A unit with this symbol already exists", 409)
    unit = Unit(name=data.name.strip(), symbol=symbol, unit_type=data.unit_type, is_active=data.is_active)
    db.add(unit)
    db.flush()
    return unit


def update_unit(db: Session, unit: Unit, data: UnitUpdate) -> Unit:
    changes = data.model_dump(exclude_unset=True)
    if "symbol" in changes and changes["symbol"] is not None:
        symbol = changes["symbol"].strip()
        clash = db.scalar(select(Unit).where(Unit.symbol == symbol, Unit.id != unit.id))
        if clash is not None:
            raise CatalogueError("A unit with this symbol already exists", 409)
        unit.symbol = symbol
    if "name" in changes and changes["name"] is not None:
        unit.name = changes["name"].strip()
    if "unit_type" in changes and changes["unit_type"] is not None:
        unit.unit_type = changes["unit_type"]
    if "is_active" in changes and changes["is_active"] is not None:
        unit.is_active = changes["is_active"]
    db.flush()
    return unit


def delete_unit(db: Session, unit: Unit) -> None:
    in_use = any(
        [
            db.scalar(select(CategoryAttribute.id).where(CategoryAttribute.unit_id == unit.id)),
            db.scalar(
                select(Product.id).where(
                    Product.deleted_at.is_(None),
                    or_(
                        Product.base_unit_id == unit.id,
                        Product.selling_unit_id == unit.id,
                        Product.net_quantity_unit_id == unit.id,
                    ),
                )
            ),
        ]
    )
    if in_use:
        raise CatalogueError("This unit is used by products or attributes. Deactivate it instead.", 409)
    db.delete(unit)
    db.flush()
