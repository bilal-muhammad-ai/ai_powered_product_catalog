from app.models.enums import AttributeScope, DataType
from app.schemas.attribute import AttributeCreate
from app.schemas.category import CategoryCreate
from app.services.attribute_schema import effective_attributes
from app.services.categories import create_category
from app.services import attribute_schema


def test_effective_attributes_follow_inheritance(db):
    parent = create_category(db, CategoryCreate(name="Aggregates"))
    child = create_category(db, CategoryCreate(name="Sand", parent_id=parent.id))
    attribute_schema.create_attribute(
        db,
        parent.id,
        AttributeCreate(
            name="Washed",
            code="washed",
            data_type=DataType.boolean,
            scope=AttributeScope.product,
            inherit_to_children=True,
        ),
    )
    attribute_schema.create_attribute(
        db,
        parent.id,
        AttributeCreate(
            name="Private note",
            code="private_note",
            data_type=DataType.text,
            scope=AttributeScope.product,
            inherit_to_children=False,
        ),
    )
    attribute_schema.create_attribute(
        db,
        child.id,
        AttributeCreate(
            name="Nominal size",
            code="nominal_size",
            data_type=DataType.text,
            scope=AttributeScope.product,
        ),
    )

    codes = [item.code for item in effective_attributes(db, child.id, active_only=True, include_inherited=True)]
    assert codes == ["nominal_size", "washed"] or set(codes) == {"nominal_size", "washed"}
    assert "private_note" not in codes
