import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import CatalogueError
from app.core.text import retired_key, slugify
from app.models.attribute import AttributeOption, CategoryAttribute
from app.models.category import Category
from app.models.enums import DataType, InventoryTransactionStatus, ProductStatus
from app.models.inventory import InventoryTransaction, InventoryTransactionItem, StockBalance
from app.models.product import Product, ProductAttributeMultiOption, ProductAttributeValue
from app.models.unit import Unit
from app.schemas.product import AttributeValueOut, ProductDetail, ProductListItem, ProductWrite
from app.services.attribute_schema import effective_attributes
from app.services.category_lookup import get_category
from app.services.product_values import FieldErrors, PreparedValue, collect_values


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))


def _like(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _unique_slug(db: Session, base: str, exclude_id: uuid.UUID | None = None) -> str:
    slug = base
    number = 2
    while True:
        stmt = select(Product.id).where(Product.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(Product.id != exclude_id)
        if db.scalar(stmt) is None:
            return slug
        slug = f"{base}-{number}"
        number += 1


def _product_options():
    return (
        selectinload(Product.category),
        selectinload(Product.attribute_values).selectinload(ProductAttributeValue.attribute),
        selectinload(Product.multi_options).selectinload(ProductAttributeMultiOption.attribute),
    )


def get_product(db: Session, product_id: uuid.UUID) -> Product:
    product = db.scalar(
        select(Product)
        .where(Product.id == product_id, Product.deleted_at.is_(None))
        .options(*_product_options())
    )
    if product is None:
        raise CatalogueError("Product not found", 404)
    return product


def _assert_unique(
    db: Session,
    column,
    value: str | None,
    exclude_id: uuid.UUID | None,
    message: str,
) -> None:
    if not value:
        return
    stmt = select(Product.id).where(column == value)
    if exclude_id is not None:
        stmt = stmt.where(Product.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise CatalogueError(message, 409)


def get_unit_if_present(db: Session, unit_id: uuid.UUID, errors: FieldErrors, field_name: str) -> None:
    unit = db.get(Unit, unit_id)
    if unit is None:
        errors.add(field_name, "Unit not found")


def save_product(db: Session, data: ProductWrite, product: Product | None = None) -> Product:
    category = get_category(db, data.category_id)
    errors = FieldErrors()
    if data.base_unit_id is not None:
        get_unit_if_present(db, data.base_unit_id, errors, "base_unit_id")
    get_unit_if_present(db, data.selling_unit_id, errors, "selling_unit_id")
    if data.net_quantity is not None and data.net_quantity_unit_id is None:
        errors.add("net_quantity_unit_id", "Choose a unit for the net quantity")
    if data.net_quantity_unit_id is not None:
        get_unit_if_present(db, data.net_quantity_unit_id, errors, "net_quantity_unit_id")
    schema = effective_attributes(db, category.id, active_only=True, include_inherited=True)
    allowed = {item.id: item for item in schema}
    product_values = collect_values(
        db,
        schema,
        data.attribute_values,
        allowed,
        errors,
        "attribute_values",
    )
    exclude_id = product.id if product else None
    if not errors.items:
        _assert_unique(db, Product.code, data.code, exclude_id, "A product with this code already exists")
        _assert_unique(db, Product.sku, data.sku, exclude_id, "SKU already exists")
        _assert_unique(db, Product.barcode, data.barcode, exclude_id, "Barcode already exists")
    if errors.items:
        raise CatalogueError("The product does not match its category", 422, errors.items)

    commercial = {
        "sku": data.sku,
        "barcode": data.barcode,
        "selling_unit_id": data.selling_unit_id,
        "net_quantity": data.net_quantity,
        "net_quantity_unit_id": data.net_quantity_unit_id,
        "cost_price": _money(data.cost_price),
        "selling_price": _money(data.selling_price),
        "currency_code": data.currency_code,
    }
    if product is None:
        product = Product(
            category_id=category.id,
            name=data.name,
            slug=_unique_slug(db, slugify(data.slug or data.name)),
            code=data.code,
            description=data.description,
            status=data.status,
            base_unit_id=data.base_unit_id,
            **commercial,
        )
        db.add(product)
        db.flush()
    else:
        if product.selling_unit_id != data.selling_unit_id and _inventory_recorded(db, product.id):
            raise CatalogueError("Selling unit cannot change after inventory has been recorded", 409)
        product.category_id = category.id
        product.name = data.name
        if data.slug:
            product.slug = _unique_slug(db, slugify(data.slug), exclude_id=product.id)
        product.code = data.code
        product.description = data.description
        product.status = data.status
        product.base_unit_id = data.base_unit_id
        for field_name, value in commercial.items():
            setattr(product, field_name, value)
        _clear_children(db, product)
        db.flush()

    _write_product_values(db, product, product_values)
    db.flush()
    product_id = product.id
    db.expire_all()
    return get_product(db, product_id)


def _clear_children(db: Session, product: Product) -> None:
    for row in list(product.multi_options):
        db.delete(row)
    for row in list(product.attribute_values):
        db.delete(row)


def _write_product_values(db: Session, product: Product, values: list[PreparedValue]) -> None:
    for item in values:
        if item.attribute.data_type == DataType.multi_select:
            for option_id in item.option_ids:
                db.add(
                    ProductAttributeMultiOption(
                        product_id=product.id,
                        attribute_id=item.attribute.id,
                        option_id=option_id,
                    )
                )
            continue
        db.add(
            ProductAttributeValue(
                product_id=product.id,
                attribute_id=item.attribute.id,
                value_text=item.value_text,
                value_numeric=item.value_numeric,
                value_boolean=item.value_boolean,
                value_date=item.value_date,
                option_id=item.option_id,
            )
        )


def _inventory_recorded(db: Session, product_id: uuid.UUID) -> bool:
    if db.scalar(select(StockBalance.id).where(StockBalance.product_id == product_id)) is not None:
        return True
    posted = db.scalar(
        select(InventoryTransactionItem.id)
        .join(InventoryTransaction, InventoryTransaction.id == InventoryTransactionItem.transaction_id)
        .where(
            InventoryTransactionItem.product_id == product_id,
            InventoryTransaction.status.in_(
                (InventoryTransactionStatus.posted, InventoryTransactionStatus.reversed)
            ),
        )
    )
    return posted is not None


def delete_product(db: Session, product: Product) -> None:
    from datetime import datetime, timezone

    balance = db.scalar(select(StockBalance).where(StockBalance.product_id == product.id))
    if balance is not None and balance.quantity_on_hand > 0:
        raise CatalogueError("This product still has stock on hand", 409)
    product.deleted_at = datetime.now(timezone.utc)
    product.slug = retired_key(product.slug, product.id, 220)
    product.code = None
    product.sku = retired_key(product.sku, product.id, 64)
    product.barcode = None
    db.flush()


def _value_out(attribute: CategoryAttribute, value: object) -> AttributeValueOut:
    return AttributeValueOut(
        attribute_id=attribute.id,
        code=attribute.code,
        name=attribute.name,
        data_type=attribute.data_type,
        value=value,
    )


def to_detail(product: Product) -> ProductDetail:
    multi_by_attribute: dict[uuid.UUID, list[uuid.UUID]] = {}
    multi_attributes: dict[uuid.UUID, CategoryAttribute] = {}
    for row in product.multi_options:
        multi_by_attribute.setdefault(row.attribute_id, []).append(row.option_id)
        multi_attributes[row.attribute_id] = row.attribute
    attribute_values = [
        _value_out(row.attribute, _stored_value(row))
        for row in sorted(product.attribute_values, key=lambda item: item.attribute.sort_order)
    ]
    for attribute_id, option_ids in multi_by_attribute.items():
        attribute_values.append(_value_out(multi_attributes[attribute_id], option_ids))
    return ProductDetail(
        id=product.id,
        category_id=product.category_id,
        category_name=product.category.name,
        base_unit_id=product.base_unit_id,
        sku=product.sku,
        barcode=product.barcode,
        name=product.name,
        slug=product.slug,
        code=product.code,
        description=product.description,
        selling_unit_id=product.selling_unit_id,
        net_quantity=product.net_quantity,
        net_quantity_unit_id=product.net_quantity_unit_id,
        cost_price=product.cost_price,
        selling_price=product.selling_price,
        currency_code=product.currency_code,
        status=product.status,
        attribute_values=attribute_values,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def _stored_value(row: ProductAttributeValue) -> object:
    data_type = row.attribute.data_type
    if data_type == DataType.text:
        return row.value_text
    if data_type == DataType.number:
        return row.value_numeric
    if data_type == DataType.boolean:
        return row.value_boolean
    if data_type == DataType.date:
        return row.value_date
    return row.option_id


def parse_attr_filters(raw_filters: list[str]) -> list[tuple[str, str]]:
    parsed: list[tuple[str, str]] = []
    for raw in raw_filters:
        if ":" not in raw:
            raise CatalogueError("Attribute filters must look like code:value", 422)
        code, value = raw.split(":", 1)
        code = code.strip()
        value = value.strip()
        if not code or not value:
            raise CatalogueError("Attribute filters must look like code:value", 422)
        parsed.append((code, value))
    return parsed


def _matches_attribute(code: str, raw: str):
    value_clauses = [
        func.lower(AttributeOption.value) == raw.lower(),
        func.lower(ProductAttributeValue.value_text) == raw.lower(),
    ]
    number = _try_decimal(raw)
    if number is not None:
        value_clauses.append(ProductAttributeValue.value_numeric == number)
    if raw.lower() in {"true", "false"}:
        value_clauses.append(ProductAttributeValue.value_boolean == (raw.lower() == "true"))
    parsed_date = _try_date(raw)
    if parsed_date is not None:
        value_clauses.append(ProductAttributeValue.value_date == parsed_date)

    product_match = exists(
        select(ProductAttributeValue.id)
        .join(CategoryAttribute, CategoryAttribute.id == ProductAttributeValue.attribute_id)
        .outerjoin(AttributeOption, AttributeOption.id == ProductAttributeValue.option_id)
        .where(
            ProductAttributeValue.product_id == Product.id,
            CategoryAttribute.code == code,
            or_(*value_clauses),
        )
    )
    multi_match = exists(
        select(ProductAttributeMultiOption.product_id)
        .join(CategoryAttribute, CategoryAttribute.id == ProductAttributeMultiOption.attribute_id)
        .join(AttributeOption, AttributeOption.id == ProductAttributeMultiOption.option_id)
        .where(
            ProductAttributeMultiOption.product_id == Product.id,
            CategoryAttribute.code == code,
            func.lower(AttributeOption.value) == raw.lower(),
        )
    )
    return or_(product_match, multi_match)


def _try_decimal(raw: str) -> Decimal | None:
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def _try_date(raw: str) -> date | None:
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def list_products(
    db: Session,
    *,
    page: int,
    page_size: int,
    q: str | None,
    category_id: uuid.UUID | None,
    status: ProductStatus | None,
    attr_filters: list[tuple[str, str]],
) -> tuple[list[ProductListItem], int]:
    stmt = (
        select(Product, Category.name)
        .join(Category, Category.id == Product.category_id)
        .where(Product.deleted_at.is_(None), Category.deleted_at.is_(None))
    )
    if category_id is not None:
        category = get_category(db, category_id)
        stmt = stmt.where(Category.path.startswith(category.path))
    if status:
        stmt = stmt.where(Product.status == status)
    if q:
        pattern = _like(q.strip())
        stmt = stmt.where(
            or_(
                Product.name.ilike(pattern, escape="\\"),
                Product.code.ilike(pattern, escape="\\"),
                Product.sku.ilike(pattern, escape="\\"),
                Product.slug.ilike(pattern, escape="\\"),
            )
        )
    for code, raw in attr_filters:
        stmt = stmt.where(_matches_attribute(code, raw))

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.execute(
        stmt.order_by(Product.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    items = [
        ProductListItem(
            id=product.id,
            name=product.name,
            sku=product.sku,
            code=product.code,
            slug=product.slug,
            status=product.status,
            category_id=product.category_id,
            category_name=category_name,
            selling_price=product.selling_price,
            currency_code=product.currency_code,
            updated_at=product.updated_at,
        )
        for product, category_name in rows
    ]
    return items, total
