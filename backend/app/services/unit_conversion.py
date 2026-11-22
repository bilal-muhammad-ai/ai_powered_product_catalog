"""Convert an entered quantity into the product's selling unit.

Runtime conversion reads unit_conversions. The factor groups below are seed data
written into that table; the converter does not consult them.
"""

from __future__ import annotations

import uuid
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import CatalogueError
from app.models.inventory import UnitConversion
from app.models.product import Product
from app.models.unit import Unit
from app.services.inventory_valuation import q_qty

FACTOR_PLACES = Decimal("0.00000001")

# Quantity of each symbol expressed in one base unit of that dimension.
CONVERSION_BASES: dict[str, dict[str, Decimal]] = {
    "weight": {"kg": Decimal("1"), "g": Decimal("0.001"), "ton": Decimal("1000")},
    "length": {"m": Decimal("1"), "ft": Decimal("0.3048"), "in": Decimal("0.0254")},
    "volume": {"m3": Decimal("1"), "L": Decimal("0.001"), "cft": Decimal("0.028316846592")},
    "count": {"pc": Decimal("1"), "doz": Decimal("12")},
}


def conversion_factor(db: Session, source: Unit, target: Unit) -> Decimal | None:
    if source.id == target.id:
        return Decimal(1)
    if source.unit_type != target.unit_type:
        return None
    graph: dict[uuid.UUID, list[tuple[uuid.UUID, Decimal]]] = {}
    for row in db.scalars(select(UnitConversion)).all():
        graph.setdefault(row.from_unit_id, []).append((row.to_unit_id, row.factor))
        graph.setdefault(row.to_unit_id, []).append((row.from_unit_id, Decimal(1) / row.factor))
    visited = {source.id}
    queue: list[tuple[uuid.UUID, Decimal]] = [(source.id, Decimal(1))]
    while queue:
        current, factor = queue.pop(0)
        for nxt, edge in graph.get(current, []):
            if nxt in visited:
                continue
            combined = factor * edge
            if nxt == target.id:
                return combined
            visited.add(nxt)
            queue.append((nxt, combined))
    return None


def to_selling_quantity(db: Session, product: Product, unit_id: uuid.UUID, quantity: Decimal) -> Decimal:
    if quantity < 0:
        raise CatalogueError("Quantity cannot be negative", 422)
    if quantity == 0:
        return Decimal("0.0000")
    unit = db.get(Unit, unit_id)
    if unit is None:
        raise CatalogueError("Unit not found", 422)
    if not unit.is_active:
        raise CatalogueError("Unit is inactive", 422)
    selling = db.get(Unit, product.selling_unit_id)
    if selling is None or not selling.is_active:
        raise CatalogueError("Selling unit is inactive", 422)
    if unit.id == selling.id:
        return q_qty(quantity)
    direct = conversion_factor(db, unit, selling)
    if direct is not None:
        return q_qty(quantity * direct)
    if product.net_quantity and product.net_quantity_unit_id:
        net_unit = db.get(Unit, product.net_quantity_unit_id)
        if net_unit is not None:
            if unit.id == net_unit.id:
                net_quantity = quantity
            else:
                to_net = conversion_factor(db, unit, net_unit)
                net_quantity = None if to_net is None else quantity * to_net
            if net_quantity is not None:
                return q_qty(net_quantity / product.net_quantity)
    raise CatalogueError("This unit is not compatible with the product", 422)


def sync_unit_conversions(db: Session) -> None:
    units = {unit.symbol: unit for unit in db.scalars(select(Unit)).all()}
    for group in CONVERSION_BASES.values():
        present = [(symbol, base) for symbol, base in group.items() if symbol in units]
        for source_symbol, source_base in present:
            for target_symbol, target_base in present:
                if source_symbol == target_symbol:
                    continue
                source = units[source_symbol]
                target = units[target_symbol]
                if source.unit_type != target.unit_type:
                    continue
                factor = (source_base / target_base).quantize(FACTOR_PLACES, rounding=ROUND_HALF_UP)
                existing = db.scalar(
                    select(UnitConversion).where(
                        UnitConversion.from_unit_id == source.id,
                        UnitConversion.to_unit_id == target.id,
                    )
                )
                if existing is None:
                    db.add(UnitConversion(from_unit_id=source.id, to_unit_id=target.id, factor=factor))
    db.flush()
