import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import CatalogueError
from app.core.text import slugify
from app.models.attribute import AttributeOption, CategoryAttribute
from app.models.enums import DataType
from app.models.product import ProductAttributeMultiOption, ProductAttributeValue
from app.schemas.attribute import (
    AttributeCreate,
    AttributeOptionCreate,
    AttributeOptionOut,
    AttributeOptionUpdate,
    AttributeOut,
    AttributeUpdate,
)
from app.services.category_lookup import descendants, get_category
from app.services.units import get_unit

SELECT_TYPES = {DataType.single_select, DataType.multi_select}


def category_chain(db: Session, category_id: uuid.UUID) -> list:
    category = get_category(db, category_id)
    chain = [category]
    current = category
    for _ in range(50):
        if current.parent_id is None:
            break
        parent = get_category(db, current.parent_id)
        chain.append(parent)
        current = parent
    else:
        raise CatalogueError("Category tree is too deep", 422)
    return chain


def effective_attributes(
    db: Session,
    category_id: uuid.UUID,
    *,
    active_only: bool,
    include_inherited: bool,
) -> list[CategoryAttribute]:
    chain = category_chain(db, category_id)
    category = chain[0]
    ids = [category.id] if not include_inherited else [item.id for item in chain]
    rows = list(
        db.scalars(
            select(CategoryAttribute)
            .where(CategoryAttribute.category_id.in_(ids))
            .options(
                selectinload(CategoryAttribute.options),
                selectinload(CategoryAttribute.category),
            )
        )
    )
    visible: list[CategoryAttribute] = []
    for row in rows:
        inherited = row.category_id != category.id
        if inherited and not row.inherit_to_children:
            continue
        if active_only and not row.is_active:
            continue
        visible.append(row)
    visible.sort(key=lambda row: (row.sort_order, row.name.lower()))
    return visible


def _code_for(name: str, code: str | None) -> str:
    raw = (code or name).strip().lower().replace(" ", "_").replace("-", "_")
    cleaned = slugify(raw).replace("-", "_")
    return cleaned[:80]


def assert_code_available(
    db: Session,
    category_id: uuid.UUID,
    code: str,
    inherit_to_children: bool,
    exclude_id: uuid.UUID | None = None,
) -> None:
    for attribute in effective_attributes(db, category_id, active_only=False, include_inherited=True):
        if attribute.id != exclude_id and attribute.code == code:
            raise CatalogueError(f"Code '{code}' is already used on this category or a parent", 409)
    if not inherit_to_children:
        return
    category = get_category(db, category_id)
    child_categories = descendants(db, category)
    if not child_categories:
        return
    stmt = select(CategoryAttribute).where(
        CategoryAttribute.category_id.in_([item.id for item in child_categories]),
        CategoryAttribute.code == code,
    )
    if exclude_id is not None:
        stmt = stmt.where(CategoryAttribute.id != exclude_id)
    clash = db.scalar(stmt)
    if clash is not None:
        raise CatalogueError(f"Code '{code}' is already used by a child category", 409)


def _check_bounds(min_value, max_value) -> None:
    if min_value is not None and max_value is not None and min_value > max_value:
        raise CatalogueError("Minimum value cannot be greater than the maximum", 422)


def attribute_in_use(db: Session, attribute_id: uuid.UUID) -> bool:
    return any(
        [
            db.scalar(select(ProductAttributeValue.id).where(ProductAttributeValue.attribute_id == attribute_id)),
            db.scalar(
                select(ProductAttributeMultiOption.attribute_id).where(
                    ProductAttributeMultiOption.attribute_id == attribute_id
                )
            ),
        ]
    )


def get_attribute(db: Session, attribute_id: uuid.UUID) -> CategoryAttribute:
    attribute = db.scalar(
        select(CategoryAttribute)
        .where(CategoryAttribute.id == attribute_id)
        .options(selectinload(CategoryAttribute.options), selectinload(CategoryAttribute.category))
    )
    if attribute is None:
        raise CatalogueError("Attribute not found", 404)
    return attribute


def create_attribute(db: Session, category_id: uuid.UUID, data: AttributeCreate) -> CategoryAttribute:
    get_category(db, category_id)
    _check_bounds(data.min_value, data.max_value)
    if data.unit_id is not None:
        get_unit(db, data.unit_id)
    code = _code_for(data.name, data.code)
    assert_code_available(db, category_id, code, data.inherit_to_children)
    attribute = CategoryAttribute(
        category_id=category_id,
        code=code,
        name=data.name.strip(),
        data_type=data.data_type,
        unit_id=data.unit_id,
        is_required=data.is_required,
        is_filterable=data.is_filterable,
        is_active=data.is_active,
        inherit_to_children=data.inherit_to_children,
        sort_order=data.sort_order,
        help_text=data.help_text,
        min_value=data.min_value,
        max_value=data.max_value,
        max_length=data.max_length,
    )
    db.add(attribute)
    db.flush()
    return get_attribute(db, attribute.id)


def update_attribute(db: Session, attribute: CategoryAttribute, data: AttributeUpdate) -> CategoryAttribute:
    changes = data.model_dump(exclude_unset=True)
    in_use = attribute_in_use(db, attribute.id)
    data_type = changes.get("data_type", attribute.data_type)
    if in_use and data_type != attribute.data_type:
        raise CatalogueError("Data type cannot change after values have been saved", 409)
    min_value = changes["min_value"] if "min_value" in changes else attribute.min_value
    max_value = changes["max_value"] if "max_value" in changes else attribute.max_value
    _check_bounds(min_value, max_value)
    if changes.get("clear_unit"):
        attribute.unit_id = None
    elif "unit_id" in changes:
        if changes["unit_id"] is not None:
            get_unit(db, changes["unit_id"])
        attribute.unit_id = changes["unit_id"]
    code = attribute.code
    inherit = attribute.inherit_to_children
    if "code" in changes and changes["code"]:
        code = _code_for(attribute.name, changes["code"])
    if "inherit_to_children" in changes and changes["inherit_to_children"] is not None:
        inherit = changes["inherit_to_children"]
    if code != attribute.code or inherit != attribute.inherit_to_children:
        assert_code_available(db, attribute.category_id, code, inherit, exclude_id=attribute.id)
    attribute.code = code
    attribute.inherit_to_children = inherit
    attribute.data_type = data_type
    if "name" in changes and changes["name"]:
        attribute.name = changes["name"].strip()
    for field in ("is_required", "is_filterable", "is_active", "sort_order", "help_text", "min_value", "max_value", "max_length"):
        if field in changes:
            setattr(attribute, field, changes[field])
    db.flush()
    return get_attribute(db, attribute.id)


def delete_attribute(db: Session, attribute: CategoryAttribute) -> None:
    if attribute_in_use(db, attribute.id):
        raise CatalogueError("This attribute has product values. Deactivate it instead of deleting it.", 409)
    db.delete(attribute)
    db.flush()


def to_attribute_out(attribute: CategoryAttribute, *, inherited: bool, active_only: bool) -> AttributeOut:
    options = sorted(attribute.options, key=lambda option: (option.sort_order, option.label.lower()))
    if active_only:
        options = [option for option in options if option.is_active]
    return AttributeOut(
        id=attribute.id,
        category_id=attribute.category_id,
        owner_category_name=attribute.category.name,
        code=attribute.code,
        name=attribute.name,
        data_type=attribute.data_type,
        unit_id=attribute.unit_id,
        is_required=attribute.is_required,
        is_filterable=attribute.is_filterable,
        is_active=attribute.is_active,
        inherit_to_children=attribute.inherit_to_children,
        sort_order=attribute.sort_order,
        help_text=attribute.help_text,
        min_value=attribute.min_value,
        max_value=attribute.max_value,
        max_length=attribute.max_length,
        inherited=inherited,
        options=[AttributeOptionOut.model_validate(option) for option in options],
        created_at=attribute.created_at,
        updated_at=attribute.updated_at,
    )


def list_effective(
    db: Session,
    category_id: uuid.UUID,
    *,
    include_inherited: bool,
    active_only: bool,
) -> list[AttributeOut]:
    category = get_category(db, category_id)
    rows = effective_attributes(
        db,
        category_id,
        active_only=active_only,
        include_inherited=include_inherited,
    )
    return [
        to_attribute_out(row, inherited=row.category_id != category.id, active_only=active_only) for row in rows
    ]


def get_option(db: Session, option_id: uuid.UUID) -> AttributeOption:
    option = db.get(AttributeOption, option_id)
    if option is None:
        raise CatalogueError("Option not found", 404)
    return option


def _option_in_use(db: Session, option_id: uuid.UUID) -> bool:
    return any(
        [
            db.scalar(select(ProductAttributeValue.id).where(ProductAttributeValue.option_id == option_id)),
            db.scalar(
                select(ProductAttributeMultiOption.option_id).where(ProductAttributeMultiOption.option_id == option_id)
            ),
        ]
    )


def create_option(db: Session, attribute: CategoryAttribute, data: AttributeOptionCreate) -> AttributeOption:
    if attribute.data_type not in SELECT_TYPES:
        raise CatalogueError("Options belong on select attributes", 422)
    value = (data.value or data.label).strip()
    if not value:
        raise CatalogueError("Option value is required", 422)
    clash = db.scalar(
        select(AttributeOption).where(
            AttributeOption.attribute_id == attribute.id,
            AttributeOption.value == value,
        )
    )
    if clash is not None:
        raise CatalogueError("This option value already exists", 409)
    option = AttributeOption(
        attribute_id=attribute.id,
        label=data.label.strip(),
        value=value,
        sort_order=data.sort_order,
        is_active=data.is_active,
    )
    db.add(option)
    db.flush()
    return option


def update_option(db: Session, option: AttributeOption, data: AttributeOptionUpdate) -> AttributeOption:
    changes = data.model_dump(exclude_unset=True)
    if "value" in changes and changes["value"]:
        value = changes["value"].strip()
        clash = db.scalar(
            select(AttributeOption).where(
                AttributeOption.attribute_id == option.attribute_id,
                AttributeOption.value == value,
                AttributeOption.id != option.id,
            )
        )
        if clash is not None:
            raise CatalogueError("This option value already exists", 409)
        option.value = value
    if "label" in changes and changes["label"]:
        option.label = changes["label"].strip()
    if "sort_order" in changes and changes["sort_order"] is not None:
        option.sort_order = changes["sort_order"]
    if "is_active" in changes and changes["is_active"] is not None:
        option.is_active = changes["is_active"]
    db.flush()
    return option


def delete_option(db: Session, option: AttributeOption) -> None:
    if _option_in_use(db, option.id):
        raise CatalogueError("This option is used by products. Deactivate it instead of deleting it.", 409)
    db.delete(option)
    db.flush()
