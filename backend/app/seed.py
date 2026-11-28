"""Load the construction catalogue seed.

Records are matched on natural keys (unit symbol, category slug, attribute code,
option value, product code). A second run inserts only what is missing.
Existing products are left as they are.

An older catalogue on the same slugs is adapted in place: categories move to the
seed's place in the tree, matching attributes take the seed's unit and bounds,
and required attributes the seed no longer uses are deactivated.
"""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.exceptions import CatalogueError
from app.models.attribute import AttributeOption, CategoryAttribute
from app.models.category import Category
from app.models.enums import DataType
from app.models.product import Product
from app.models.unit import Unit
from app.schemas.attribute import AttributeCreate, AttributeOptionCreate, AttributeUpdate
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.schemas.product import AttributeValueIn, ProductWrite
from app.schemas.unit import UnitCreate
from app.seed_data.catalogue import (
    CATEGORIES,
    PRODUCTS,
    UNITS,
    AttributeSeed,
    AttributeValue,
    CategorySeed,
    OptionSeed,
    ProductSeed,
    UnitSeed,
)
from app.services.attribute_schema import (
    attribute_in_use,
    create_attribute,
    create_option,
    effective_attributes,
    update_attribute,
)
from app.services.categories import create_category, update_category
from app.services.products import save_product
from app.services.units import create_unit
from app.services.unit_conversion import sync_unit_conversions


@dataclass
class SeedCounts:
    units: int = 0
    categories: int = 0
    attributes: int = 0
    options: int = 0
    products: int = 0


@dataclass
class SeedResult:
    created: SeedCounts = field(default_factory=SeedCounts)
    skipped: SeedCounts = field(default_factory=SeedCounts)


def _unit(db: Session, spec: UnitSeed) -> tuple[uuid.UUID, bool]:
    existing = db.scalar(select(Unit).where(Unit.symbol == spec.symbol))
    if existing is not None:
        return existing.id, False
    created = create_unit(
        db,
        UnitCreate(name=spec.name, symbol=spec.symbol, unit_type=spec.unit_type),
    )
    return created.id, True


def _category(db: Session, spec: CategorySeed) -> tuple[uuid.UUID, bool]:
    existing = db.scalar(
        select(Category).where(Category.slug == spec.slug, Category.deleted_at.is_(None))
    )
    if existing is not None:
        update_category(
            db,
            existing,
            CategoryUpdate(
                name=spec.name,
                description=spec.description,
                sort_order=spec.sort_order,
                parent_id=None,
            ),
        )
        return existing.id, False
    created = create_category(
        db,
        CategoryCreate(
            name=spec.name,
            slug=spec.slug,
            description=spec.description,
            sort_order=spec.sort_order,
        ),
    )
    return created.id, True


def _attribute(
    db: Session,
    category_id: uuid.UUID,
    spec: AttributeSeed,
    units: dict[str, uuid.UUID],
) -> tuple[CategoryAttribute, bool]:
    existing = db.scalar(
        select(CategoryAttribute).where(
            CategoryAttribute.category_id == category_id,
            CategoryAttribute.code == spec.code,
        )
    )
    if existing is not None:
        _align_attribute(db, existing, spec, units)
        return existing, False
    unit_id = _unit_id(units, spec.unit_symbol, f"attribute {spec.code}")
    created = create_attribute(
        db,
        category_id,
        AttributeCreate(
            name=spec.name,
            code=spec.code,
            data_type=spec.data_type,
            unit_id=unit_id,
            is_required=spec.is_required,
            is_filterable=spec.is_filterable,
            inherit_to_children=True,
            sort_order=spec.sort_order,
            help_text=spec.help_text,
            min_value=spec.min_value,
            max_value=spec.max_value,
        ),
    )
    return created, True


def _option(db: Session, attribute: CategoryAttribute, spec: OptionSeed, sort_order: int) -> bool:
    existing = db.scalar(
        select(AttributeOption).where(
            AttributeOption.attribute_id == attribute.id,
            AttributeOption.value == spec.value,
        )
    )
    if existing is not None:
        return False
    create_option(
        db,
        attribute,
        AttributeOptionCreate(label=spec.label, value=spec.value, sort_order=sort_order),
    )
    return True


def _unit_id(units: dict[str, uuid.UUID], symbol: str | None, owner: str) -> uuid.UUID | None:
    if symbol is None:
        return None
    try:
        return units[symbol]
    except KeyError as exc:
        raise RuntimeError(f"{owner} uses unknown unit '{symbol}'") from exc


def _attributes_by_code(db: Session, category_id: uuid.UUID) -> dict[str, CategoryAttribute]:
    rows = db.scalars(select(CategoryAttribute).where(CategoryAttribute.category_id == category_id)).all()
    return {row.code: row for row in rows}


def _one_value(db: Session, attribute: CategoryAttribute, raw: AttributeValue, owner: str) -> AttributeValueIn:
    if attribute.data_type == DataType.single_select:
        if not isinstance(raw, str):
            raise RuntimeError(f"{owner} attribute '{attribute.code}' needs an option value")
        option = db.scalar(
            select(AttributeOption).where(
                AttributeOption.attribute_id == attribute.id,
                AttributeOption.value == raw,
            )
        )
        if option is None:
            raise RuntimeError(f"{owner} attribute '{attribute.code}' has no option '{raw}'")
        return AttributeValueIn(attribute_id=attribute.id, value=option.id)
    if attribute.data_type == DataType.number:
        return AttributeValueIn(attribute_id=attribute.id, value=Decimal(str(raw)))
    if attribute.data_type == DataType.text:
        return AttributeValueIn(attribute_id=attribute.id, value=str(raw))
    if attribute.data_type == DataType.boolean:
        if not isinstance(raw, bool):
            raise RuntimeError(f"{owner} attribute '{attribute.code}' needs true or false")
        return AttributeValueIn(attribute_id=attribute.id, value=raw)
    raise RuntimeError(f"{owner} attribute '{attribute.code}' has unsupported type {attribute.data_type}")


def _values(
    db: Session,
    attributes: dict[str, CategoryAttribute],
    raw_values: dict[str, AttributeValue],
    owner: str,
) -> list[AttributeValueIn]:
    prepared: list[AttributeValueIn] = []
    for code, raw in raw_values.items():
        attribute = attributes.get(code)
        if attribute is None:
            raise RuntimeError(f"{owner} uses unknown attribute '{code}'")
        prepared.append(_one_value(db, attribute, raw, owner))
    return prepared


def _align_attribute(
    db: Session,
    attribute: CategoryAttribute,
    spec: AttributeSeed,
    units: dict[str, uuid.UUID],
) -> None:
    expected_unit = _unit_id(units, spec.unit_symbol, f"attribute {spec.code}")
    in_use = attribute_in_use(db, attribute.id)
    if in_use and attribute.data_type != spec.data_type:
        raise RuntimeError(
            f"Attribute '{spec.code}' already has saved values and cannot change type."
        )
    if in_use and attribute.unit_id != expected_unit:
        raise RuntimeError(
            f"Attribute '{spec.code}' already has saved values and cannot change unit."
        )
    try:
        update_attribute(
            db,
            attribute,
            AttributeUpdate(
                name=spec.name,
                data_type=spec.data_type,
                unit_id=expected_unit,
                is_required=spec.is_required,
                is_filterable=spec.is_filterable,
                is_active=True,
                sort_order=spec.sort_order,
                help_text=spec.help_text,
                min_value=spec.min_value,
                max_value=spec.max_value,
            ),
        )
    except CatalogueError as exc:
        raise RuntimeError(f"Attribute '{spec.code}' could not be aligned: {exc.message}") from exc


def _retire_undefined(db: Session, category_id: uuid.UUID, spec: CategorySeed) -> None:
    """Drop old required fields so sample products can use the seed's schema."""
    defined = {attribute.code for attribute in spec.attributes}
    rows = db.scalars(
        select(CategoryAttribute).where(CategoryAttribute.category_id == category_id)
    ).all()
    changed = False
    for attribute in rows:
        if attribute.code in defined:
            continue
        if attribute.is_required or attribute.is_active:
            attribute.is_required = False
            attribute.is_active = False
            changed = True
    if changed:
        db.flush()


def _category_spec(slug: str) -> CategorySeed:
    for spec in CATEGORIES:
        if spec.slug == slug:
            return spec
    raise RuntimeError(f"Unknown seed category '{slug}'")


def _assert_compatible(
    db: Session,
    category_id: uuid.UUID,
    spec: ProductSeed,
    units: dict[str, uuid.UUID],
) -> None:
    """Refuse to attach sample products to a category shaped by a different seed."""
    schema = {
        attribute.code: attribute
        for attribute in effective_attributes(
            db,
            category_id,
            active_only=True,
            include_inherited=True,
        )
    }
    defined = {attribute.code: attribute for attribute in _category_spec(spec.category_slug).attributes}
    for code, expected in defined.items():
        current = schema.get(code)
        if current is None:
            raise RuntimeError(f"Category '{spec.category_slug}' is missing attribute '{code}'")
        if current.data_type != expected.data_type:
            raise RuntimeError(
                f"Category '{spec.category_slug}' attribute '{code}' does not match this seed. "
                "Load the seed into an empty database."
            )
        expected_unit = units[expected.unit_symbol] if expected.unit_symbol else None
        if current.unit_id != expected_unit:
            raise RuntimeError(
                f"Category '{spec.category_slug}' attribute '{code}' uses a different unit. "
                "Load the seed into an empty database."
            )
    for attribute in schema.values():
        if not attribute.is_required:
            continue
        if attribute.code not in spec.attributes:
            raise RuntimeError(
                f"Category '{spec.category_slug}' already requires '{attribute.code}', "
                "which this seed does not set. Load the seed into an empty database."
            )


def _product(
    db: Session,
    spec: ProductSeed,
    categories: dict[str, uuid.UUID],
    units: dict[str, uuid.UUID],
) -> bool:
    existing = db.scalar(
        select(Product.id).where(Product.code == spec.code, Product.deleted_at.is_(None))
    )
    if existing is not None:
        return False
    try:
        category_id = categories[spec.category_slug]
    except KeyError as exc:
        raise RuntimeError(f"{spec.code} uses unknown category '{spec.category_slug}'") from exc
    _assert_compatible(db, category_id, spec, units)
    attributes = _attributes_by_code(db, category_id)
    selling_unit_id = _unit_id(units, spec.selling_unit, spec.code)
    if selling_unit_id is None:
        raise RuntimeError(f"{spec.code} needs a selling unit")
    payload = ProductWrite(
        category_id=category_id,
        name=spec.name,
        sku=spec.sku,
        code=spec.code,
        description=spec.description,
        status=spec.status,
        base_unit_id=_unit_id(units, spec.base_unit, spec.code),
        selling_unit_id=selling_unit_id,
        net_quantity=spec.net_quantity,
        net_quantity_unit_id=_unit_id(units, spec.net_quantity_unit, spec.code),
        selling_price=spec.selling_price,
        attribute_values=_values(db, attributes, spec.attributes, spec.code),
    )
    try:
        save_product(db, payload)
    except CatalogueError as exc:
        detail = "; ".join(f"{item['field']}: {item['message']}" for item in exc.errors)
        message = f"{spec.code}: {exc.message}"
        if detail:
            message = f"{message} ({detail})"
        raise RuntimeError(message) from exc
    return True


def seed(db: Session) -> SeedResult:
    result = SeedResult()
    units: dict[str, uuid.UUID] = {}
    for spec in UNITS:
        unit_id, created = _unit(db, spec)
        units[spec.symbol] = unit_id
        bucket = result.created if created else result.skipped
        bucket.units += 1
    sync_unit_conversions(db)

    categories: dict[str, uuid.UUID] = {}
    for spec in CATEGORIES:
        category_id, created = _category(db, spec)
        categories[spec.slug] = category_id
        bucket = result.created if created else result.skipped
        bucket.categories += 1
        for attribute_spec in spec.attributes:
            attribute, attribute_created = _attribute(db, category_id, attribute_spec, units)
            attribute_bucket = result.created if attribute_created else result.skipped
            attribute_bucket.attributes += 1
            for index, option_spec in enumerate(attribute_spec.options):
                option_created = _option(db, attribute, option_spec, index)
                option_bucket = result.created if option_created else result.skipped
                option_bucket.options += 1
        _retire_undefined(db, category_id, spec)

    for spec in PRODUCTS:
        created = _product(db, spec, categories, units)
        bucket = result.created if created else result.skipped
        bucket.products += 1
    return result


def main() -> None:
    with SessionLocal() as db:
        try:
            result = seed(db)
            db.commit()
        except Exception:
            db.rollback()
            raise
    created = result.created
    skipped = result.skipped
    print(
        "Construction catalogue seed complete. "
        f"Created {created.units} units, {created.categories} categories, "
        f"{created.attributes} attributes, {created.options} options, "
        f"{created.products} products. "
        f"Already present: {skipped.units} units, {skipped.categories} categories, "
        f"{skipped.attributes} attributes, {skipped.options} options, "
        f"{skipped.products} products."
    )


if __name__ == "__main__":
    main()
