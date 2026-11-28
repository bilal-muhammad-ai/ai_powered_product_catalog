from decimal import Decimal

from sqlalchemy import select

from app.models.attribute import AttributeOption, CategoryAttribute
from app.models.category import Category
from app.models.enums import DataType, UnitType
from app.models.product import Product
from app.models.unit import Unit
from app.schemas.attribute import AttributeCreate
from app.schemas.category import CategoryCreate
from app.schemas.unit import UnitCreate
from app.seed import seed
from app.seed_data.catalogue import CATEGORIES, CEMENT_BRANDS, PRODUCTS, UNITS
from app.services.attribute_schema import create_attribute
from app.services.categories import create_category
from app.services.units import create_unit


def test_seed_loads_catalogue_and_is_idempotent(db):
    first = seed(db)
    second = seed(db)

    assert first.created.units == len(UNITS)
    assert first.created.categories == len(CATEGORIES)
    assert first.created.products == len(PRODUCTS)
    assert second.created.units == 0
    assert second.created.categories == 0
    assert second.created.attributes == 0
    assert second.created.options == 0
    assert second.created.products == 0
    assert second.skipped.units == first.created.units
    assert second.skipped.categories == first.created.categories
    assert second.skipped.attributes == first.created.attributes
    assert second.skipped.options == first.created.options
    assert second.skipped.products == first.created.products

    symbols = set(db.scalars(select(Unit.symbol)))
    assert {unit.symbol for unit in UNITS} <= symbols

    for category_spec in CATEGORIES:
        category = db.scalar(select(Category).where(Category.slug == category_spec.slug))
        assert category is not None
        assert category.name == category_spec.name
        codes = set(
            db.scalars(
                select(CategoryAttribute.code).where(CategoryAttribute.category_id == category.id)
            )
        )
        assert codes == {attribute.code for attribute in category_spec.attributes}

    codes = set(db.scalars(select(Product.code).where(Product.deleted_at.is_(None))))
    assert codes == {product.code for product in PRODUCTS}

    cement = db.scalar(select(Category).where(Category.slug == "cement"))
    brand = db.scalar(
        select(CategoryAttribute).where(
            CategoryAttribute.category_id == cement.id,
            CategoryAttribute.code == "brand",
        )
    )
    labels = set(db.scalars(select(AttributeOption.label).where(AttributeOption.attribute_id == brand.id)))
    assert labels == {option.label for option in CEMENT_BRANDS}

    bag = db.scalar(select(Product).where(Product.sku == "CEM-ML-OPC43-50"))
    assert bag is not None
    assert bag.code == "CEM-ML-OPC43-50"
    assert bag.name == "Maple Leaf Cement OPC 43 — 50 kg bag"
    assert bag.selling_price == Decimal("1480.00")
    assert bag.net_quantity == Decimal("50")

    small = db.scalar(select(Product).where(Product.sku == "CEM-ML-OPC43-20"))
    assert small is not None
    assert small.id != bag.id


def test_seed_adapts_an_older_catalogue(db):
    cement = create_category(db, CategoryCreate(name="Cement", slug="cement"))
    create_attribute(
        db,
        cement.id,
        AttributeCreate(
            name="Type",
            code="type",
            data_type=DataType.single_select,
            is_required=True,
        ),
    )
    aggregates = create_category(db, CategoryCreate(name="Aggregates", slug="aggregates"))
    create_category(db, CategoryCreate(name="Sand", slug="sand", parent_id=aggregates.id))
    millimetre = create_unit(db, UnitCreate(name="Millimetre", symbol="mm", unit_type=UnitType.length))
    pipes = create_category(db, CategoryCreate(name="Sanitary Pipes", slug="sanitary-pipes"))
    create_attribute(
        db,
        pipes.id,
        AttributeCreate(
            name="Diameter",
            code="diameter",
            data_type=DataType.number,
            unit_id=millimetre.id,
            is_required=True,
        ),
    )

    result = seed(db)

    assert result.created.products == len(PRODUCTS)
    old_type = db.scalar(
        select(CategoryAttribute).where(
            CategoryAttribute.category_id == cement.id,
            CategoryAttribute.code == "type",
        )
    )
    assert old_type.is_required is False
    assert old_type.is_active is False

    sand = db.scalar(select(Category).where(Category.slug == "sand"))
    assert sand.parent_id is None

    diameter = db.scalar(
        select(CategoryAttribute).where(
            CategoryAttribute.category_id == pipes.id,
            CategoryAttribute.code == "diameter",
        )
    )
    inch = db.scalar(select(Unit).where(Unit.symbol == "in"))
    assert diameter.unit_id == inch.id
