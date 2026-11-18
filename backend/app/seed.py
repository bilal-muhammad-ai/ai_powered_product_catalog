from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.attribute import AttributeOption, CategoryAttribute
from app.models.category import Category
from app.models.enums import AttributeScope, DataType, UnitType
from app.models.unit import Unit
from app.services.attribute_schema import create_attribute, create_option
from app.services.categories import create_category
from app.services.units import create_unit
from app.schemas.attribute import AttributeCreate, AttributeOptionCreate
from app.schemas.category import CategoryCreate
from app.schemas.unit import UnitCreate


def _unit(db: Session, name: str, symbol: str, unit_type: UnitType) -> Unit:
    existing = db.scalar(select(Unit).where(Unit.symbol == symbol))
    if existing is not None:
        return existing
    return create_unit(db, UnitCreate(name=name, symbol=symbol, unit_type=unit_type))


def _category(db: Session, name: str, parent_id=None) -> Category:
    slug = name.lower().replace(" ", "-")
    existing = db.scalar(select(Category).where(Category.slug == slug, Category.deleted_at.is_(None)))
    if existing is not None:
        return existing
    return create_category(db, CategoryCreate(name=name, parent_id=parent_id))


def _attribute(db: Session, category: Category, **kwargs) -> CategoryAttribute:
    code = kwargs["code"]
    existing = db.scalar(
        select(CategoryAttribute).where(
            CategoryAttribute.category_id == category.id,
            CategoryAttribute.code == code,
        )
    )
    if existing is not None:
        return existing
    return create_attribute(db, category.id, AttributeCreate(**kwargs))


def _options(db: Session, attribute: CategoryAttribute, pairs: list[tuple[str, str]]) -> None:
    for index, (label, value) in enumerate(pairs):
        existing = db.scalar(
            select(AttributeOption).where(
                AttributeOption.attribute_id == attribute.id,
                AttributeOption.value == value,
            )
        )
        if existing is None:
            create_option(
                db,
                attribute,
                AttributeOptionCreate(label=label, value=value, sort_order=index),
            )


def seed(db: Session) -> None:
    kilogram = _unit(db, "Kilogram", "kg", UnitType.weight)
    _unit(db, "Gram", "g", UnitType.weight)
    _unit(db, "Tonne", "t", UnitType.weight)
    _unit(db, "Bag", "bag", UnitType.packaging)
    _unit(db, "Piece", "pcs", UnitType.count)
    meter = _unit(db, "Metre", "m", UnitType.length)
    millimetre = _unit(db, "Millimetre", "mm", UnitType.length)
    _unit(db, "Cubic metre", "m3", UnitType.volume)
    litre = _unit(db, "Litre", "L", UnitType.volume)

    cement = _category(db, "Cement")
    aggregates = _category(db, "Aggregates")
    sand = _category(db, "Sand", aggregates.id)
    gravel = _category(db, "Gravel", aggregates.id)
    steel = _category(db, "Steel")
    pipes = _category(db, "Sanitary Pipes")
    brushes = _category(db, "Brushes")
    pans = _category(db, "Head Pans")

    cement_type = _attribute(
        db,
        cement,
        name="Type",
        code="type",
        data_type=DataType.single_select,
        scope=AttributeScope.product,
        is_required=True,
        is_filterable=True,
        sort_order=1,
    )
    _options(db, cement_type, [("OPC", "opc"), ("PPC", "ppc"), ("SRC", "src")])
    grade = _attribute(
        db,
        cement,
        name="Grade",
        code="grade",
        data_type=DataType.single_select,
        scope=AttributeScope.product,
        is_required=True,
        is_filterable=True,
        sort_order=2,
    )
    _options(db, grade, [("43 Grade", "43"), ("53 Grade", "53")])
    bag_weight = _attribute(
        db,
        cement,
        name="Bag weight",
        code="bag_weight",
        data_type=DataType.single_select,
        scope=AttributeScope.variant,
        unit_id=kilogram.id,
        is_required=True,
        is_filterable=True,
        sort_order=3,
    )
    _options(db, bag_weight, [("20 kg", "20"), ("50 kg", "50")])

    washed = _attribute(
        db,
        aggregates,
        name="Washed",
        code="washed",
        data_type=DataType.boolean,
        scope=AttributeScope.product,
        is_required=True,
        is_filterable=True,
        inherit_to_children=True,
        sort_order=1,
    )
    del washed

    sand_size = _attribute(
        db,
        sand,
        name="Nominal size",
        code="nominal_size",
        data_type=DataType.single_select,
        scope=AttributeScope.product,
        is_required=True,
        is_filterable=True,
        sort_order=2,
    )
    _options(db, sand_size, [("Fine", "fine"), ("Medium", "medium"), ("Coarse", "coarse")])
    sand_pack = _attribute(
        db,
        sand,
        name="Pack",
        code="pack",
        data_type=DataType.single_select,
        scope=AttributeScope.variant,
        is_required=True,
        is_filterable=True,
        sort_order=3,
    )
    _options(db, sand_pack, [("Loose (per m³)", "loose"), ("50 kg bag", "50kg")])

    _attribute(
        db,
        gravel,
        name="Nominal size",
        code="nominal_size",
        data_type=DataType.text,
        scope=AttributeScope.product,
        is_required=True,
        is_filterable=True,
        help_text="Example: 10–20 mm",
        sort_order=2,
    )
    gravel_pack = _attribute(
        db,
        gravel,
        name="Pack",
        code="pack",
        data_type=DataType.single_select,
        scope=AttributeScope.variant,
        is_required=True,
        is_filterable=True,
        sort_order=3,
    )
    _options(db, gravel_pack, [("Loose (per m³)", "loose"), ("50 kg bag", "50kg")])

    steel_grade = _attribute(
        db,
        steel,
        name="Grade",
        code="grade",
        data_type=DataType.single_select,
        scope=AttributeScope.product,
        is_required=True,
        is_filterable=True,
        sort_order=1,
    )
    _options(db, steel_grade, [("Grade 40", "40"), ("Grade 60", "60")])
    _attribute(
        db,
        steel,
        name="Diameter",
        code="diameter",
        data_type=DataType.number,
        scope=AttributeScope.variant,
        unit_id=millimetre.id,
        is_required=True,
        is_filterable=True,
        min_value=6,
        max_value=40,
        sort_order=2,
    )
    _attribute(
        db,
        steel,
        name="Length",
        code="length",
        data_type=DataType.number,
        scope=AttributeScope.variant,
        unit_id=meter.id,
        is_required=True,
        is_filterable=True,
        min_value=1,
        max_value=12,
        sort_order=3,
    )

    material = _attribute(
        db,
        pipes,
        name="Material",
        code="material",
        data_type=DataType.single_select,
        scope=AttributeScope.product,
        is_required=True,
        is_filterable=True,
        sort_order=1,
    )
    _options(db, material, [("PVC", "pvc"), ("CPVC", "cpvc"), ("PPR", "ppr"), ("GI", "gi")])
    _attribute(
        db,
        pipes,
        name="Diameter",
        code="diameter",
        data_type=DataType.number,
        scope=AttributeScope.variant,
        unit_id=millimetre.id,
        is_required=True,
        is_filterable=True,
        sort_order=2,
    )
    _attribute(
        db,
        pipes,
        name="Length",
        code="length",
        data_type=DataType.number,
        scope=AttributeScope.variant,
        unit_id=meter.id,
        is_required=True,
        is_filterable=True,
        sort_order=3,
    )

    brush_type = _attribute(
        db,
        brushes,
        name="Brush type",
        code="brush_type",
        data_type=DataType.single_select,
        scope=AttributeScope.product,
        is_required=True,
        is_filterable=True,
        sort_order=1,
    )
    _options(db, brush_type, [("Paint", "paint"), ("Wire", "wire"), ("Broom", "broom")])
    size = _attribute(
        db,
        brushes,
        name="Size",
        code="size",
        data_type=DataType.single_select,
        scope=AttributeScope.variant,
        is_required=True,
        is_filterable=True,
        sort_order=2,
    )
    _options(db, size, [("Small", "small"), ("Medium", "medium"), ("Large", "large")])

    pan_material = _attribute(
        db,
        pans,
        name="Material",
        code="material",
        data_type=DataType.single_select,
        scope=AttributeScope.product,
        is_required=True,
        is_filterable=True,
        sort_order=1,
    )
    _options(db, pan_material, [("Plastic", "plastic"), ("Steel", "steel")])
    _attribute(
        db,
        pans,
        name="Capacity",
        code="capacity",
        data_type=DataType.number,
        scope=AttributeScope.variant,
        unit_id=litre.id,
        is_required=True,
        is_filterable=True,
        min_value=5,
        max_value=50,
        sort_order=2,
    )


def main() -> None:
    with SessionLocal() as db:
        seed(db)
        db.commit()
    print("Seeded construction catalogue")


if __name__ == "__main__":
    main()
