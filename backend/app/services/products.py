import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import CatalogueError
from app.core.text import retired_key, slugify
from app.models.attribute import AttributeOption, CategoryAttribute
from app.models.category import Category
from app.models.enums import AttributeScope, DataType, ProductStatus
from app.models.product import Product, ProductAttributeMultiOption, ProductAttributeValue
from app.models.unit import Unit
from app.models.variant import ProductVariant, VariantAttributeValue
from app.schemas.product import (
    AttributeValueOut,
    ProductDetail,
    ProductListItem,
    ProductWrite,
    VariantIn,
    VariantOut,
)
from app.services.attribute_schema import effective_attributes
from app.services.category_lookup import get_category
from app.services.product_values import FieldErrors, PreparedValue, collect_values, variant_key
from app.services.units import get_unit


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
        selectinload(Product.variants).selectinload(ProductVariant.attribute_values).selectinload(
            VariantAttributeValue.attribute
        ),
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


def _assert_code(db: Session, code: str | None, exclude_id: uuid.UUID | None) -> None:
    if not code:
        return
    stmt = select(Product.id).where(Product.code == code)
    if exclude_id is not None:
        stmt = stmt.where(Product.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise CatalogueError("A product with this code already exists", 409)


def _assert_skus(db: Session, skus: set[str], exclude_product_id: uuid.UUID | None) -> None:
    if not skus:
        return
    stmt = select(ProductVariant.sku).where(ProductVariant.sku.in_(skus))
    if exclude_product_id is not None:
        stmt = stmt.where(ProductVariant.product_id != exclude_product_id)
    taken = db.scalars(stmt).all()
    if taken:
        raise CatalogueError(f"SKU already exists: {taken[0]}", 409)


def _assert_barcodes(db: Session, barcodes: set[str], exclude_product_id: uuid.UUID | None) -> None:
    if not barcodes:
        return
    stmt = select(ProductVariant.barcode).where(ProductVariant.barcode.in_(barcodes))
    if exclude_product_id is not None:
        stmt = stmt.where(ProductVariant.product_id != exclude_product_id)
    taken = db.scalars(stmt).all()
    if taken:
        raise CatalogueError(f"Barcode already exists: {taken[0]}", 409)


def _prepare_variants(
    db: Session,
    variants: list[VariantIn],
    variant_attributes: list[CategoryAttribute],
    allowed: dict[uuid.UUID, CategoryAttribute],
    errors: FieldErrors,
) -> list[tuple[VariantIn, list[PreparedValue], str]]:
    prepared: list[tuple[VariantIn, list[PreparedValue], str]] = []
    seen_skus: set[str] = set()
    seen_barcodes: set[str] = set()
    seen_keys: set[str] = set()
    for index, variant in enumerate(variants):
        prefix = f"variants[{index}]"
        sku = variant.sku or ""
        if not sku:
            errors.add(f"{prefix}.sku", "SKU is required")
        elif sku in seen_skus:
            errors.add(f"{prefix}.sku", "SKU is repeated on this product")
        else:
            seen_skus.add(sku)
        if variant.barcode:
            if variant.barcode in seen_barcodes:
                errors.add(f"{prefix}.barcode", "Barcode is repeated on this product")
            else:
                seen_barcodes.add(variant.barcode)
        get_unit_if_present(db, variant.selling_unit_id, errors, f"{prefix}.selling_unit_id")
        if variant.net_quantity is not None and variant.net_quantity_unit_id is None:
            errors.add(f"{prefix}.net_quantity_unit_id", "Choose a unit for the net quantity")
        if variant.net_quantity_unit_id is not None:
            get_unit_if_present(db, variant.net_quantity_unit_id, errors, f"{prefix}.net_quantity_unit_id")
        values = collect_values(
            db,
            variant_attributes,
            variant.attribute_values,
            allowed,
            errors,
            f"{prefix}.attribute_values",
            AttributeScope.variant,
        )
        key = variant_key(values)
        if key in seen_keys:
            errors.add(prefix, "Another variant already uses this combination of attributes")
        else:
            seen_keys.add(key)
        prepared.append((variant, values, key))
    return prepared


def get_unit_if_present(db: Session, unit_id: uuid.UUID, errors: FieldErrors, field_name: str) -> None:
    unit = db.get(Unit, unit_id)
    if unit is None:
        errors.add(field_name, "Unit not found")


def save_product(db: Session, data: ProductWrite, product: Product | None = None) -> Product:
    category = get_category(db, data.category_id)
    errors = FieldErrors()
    if data.base_unit_id is not None:
        get_unit_if_present(db, data.base_unit_id, errors, "base_unit_id")
    schema = effective_attributes(db, category.id, active_only=True, include_inherited=True)
    allowed = {item.id: item for item in schema}
    product_attributes = [item for item in schema if item.scope == AttributeScope.product]
    variant_attributes = [item for item in schema if item.scope == AttributeScope.variant]
    product_values = collect_values(
        db,
        product_attributes,
        data.attribute_values,
        allowed,
        errors,
        "attribute_values",
        AttributeScope.product,
    )
    prepared_variants = _prepare_variants(db, data.variants, variant_attributes, allowed, errors)
    exclude_id = product.id if product else None
    if not errors.items:
        _assert_code(db, data.code, exclude_id)
        _assert_skus(db, {item[0].sku for item in prepared_variants if item[0].sku}, exclude_id)
        _assert_barcodes(
            db,
            {item[0].barcode for item in prepared_variants if item[0].barcode},
            exclude_id,
        )
    if errors.items:
        raise CatalogueError("The product does not match its category", 422, errors.items)

    if product is None:
        product = Product(
            category_id=category.id,
            name=data.name,
            slug=_unique_slug(db, slugify(data.slug or data.name)),
            code=data.code,
            description=data.description,
            status=data.status,
            base_unit_id=data.base_unit_id,
        )
        db.add(product)
        db.flush()
    else:
        product.category_id = category.id
        product.name = data.name
        if data.slug:
            product.slug = _unique_slug(db, slugify(data.slug), exclude_id=product.id)
        product.code = data.code
        product.description = data.description
        product.status = data.status
        product.base_unit_id = data.base_unit_id
        _clear_children(db, product)
        db.flush()

    _write_product_values(db, product, product_values)
    _write_variants(db, product, prepared_variants)
    db.flush()
    product_id = product.id
    db.expire_all()
    return get_product(db, product_id)


def _clear_children(db: Session, product: Product) -> None:
    for row in list(product.multi_options):
        db.delete(row)
    for row in list(product.attribute_values):
        db.delete(row)
    for row in list(product.variants):
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


def _write_variants(
    db: Session,
    product: Product,
    prepared: list[tuple[VariantIn, list[PreparedValue], str]],
) -> None:
    for index, (incoming, values, key) in enumerate(prepared):
        variant = ProductVariant(
            product_id=product.id,
            sku=incoming.sku,
            barcode=incoming.barcode,
            name=incoming.name,
            selling_unit_id=incoming.selling_unit_id,
            net_quantity=incoming.net_quantity,
            net_quantity_unit_id=incoming.net_quantity_unit_id,
            cost_price=_money(incoming.cost_price),
            selling_price=_money(incoming.selling_price),
            currency_code=incoming.currency_code,
            is_active=incoming.is_active,
            sort_order=incoming.sort_order,
            variant_key=key,
        )
        db.add(variant)
        db.flush()
        for item in values:
            db.add(
                VariantAttributeValue(
                    variant_id=variant.id,
                    attribute_id=item.attribute.id,
                    value_text=item.value_text,
                    value_numeric=item.value_numeric,
                    value_boolean=item.value_boolean,
                    value_date=item.value_date,
                    option_id=item.option_id,
                )
            )


def delete_product(db: Session, product: Product) -> None:
    from datetime import datetime, timezone

    product.deleted_at = datetime.now(timezone.utc)
    product.slug = retired_key(product.slug, product.id, 220)
    product.code = None
    for variant in list(product.variants):
        variant.sku = retired_key(variant.sku, variant.id, 64)
        variant.barcode = None
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
    variants = [
        VariantOut(
            id=variant.id,
            sku=variant.sku,
            barcode=variant.barcode,
            name=variant.name,
            selling_unit_id=variant.selling_unit_id,
            net_quantity=variant.net_quantity,
            net_quantity_unit_id=variant.net_quantity_unit_id,
            cost_price=variant.cost_price,
            selling_price=variant.selling_price,
            currency_code=variant.currency_code,
            is_active=variant.is_active,
            sort_order=variant.sort_order,
            variant_key=variant.variant_key,
            attribute_values=[
                _value_out(item.attribute, _stored_value(item))
                for item in sorted(variant.attribute_values, key=lambda row: row.attribute.sort_order)
            ],
        )
        for variant in sorted(product.variants, key=lambda item: (item.sort_order, item.sku))
    ]
    return ProductDetail(
        id=product.id,
        category_id=product.category_id,
        category_name=product.category.name,
        base_unit_id=product.base_unit_id,
        name=product.name,
        slug=product.slug,
        code=product.code,
        description=product.description,
        status=product.status,
        attribute_values=attribute_values,
        variants=variants,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def _stored_value(row: ProductAttributeValue | VariantAttributeValue) -> object:
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
    variant_clauses = [
        func.lower(AttributeOption.value) == raw.lower(),
        func.lower(VariantAttributeValue.value_text) == raw.lower(),
    ]
    number = _try_decimal(raw)
    if number is not None:
        value_clauses.append(ProductAttributeValue.value_numeric == number)
        variant_clauses.append(VariantAttributeValue.value_numeric == number)
    if raw.lower() in {"true", "false"}:
        flag = raw.lower() == "true"
        value_clauses.append(ProductAttributeValue.value_boolean == flag)
        variant_clauses.append(VariantAttributeValue.value_boolean == flag)
    parsed_date = _try_date(raw)
    if parsed_date is not None:
        value_clauses.append(ProductAttributeValue.value_date == parsed_date)
        variant_clauses.append(VariantAttributeValue.value_date == parsed_date)

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
    variant_match = exists(
        select(VariantAttributeValue.id)
        .join(ProductVariant, ProductVariant.id == VariantAttributeValue.variant_id)
        .join(CategoryAttribute, CategoryAttribute.id == VariantAttributeValue.attribute_id)
        .outerjoin(AttributeOption, AttributeOption.id == VariantAttributeValue.option_id)
        .where(
            ProductVariant.product_id == Product.id,
            CategoryAttribute.code == code,
            or_(*variant_clauses),
        )
    )
    return or_(product_match, multi_match, variant_match)


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
        sku_match = exists(
            select(ProductVariant.id).where(
                ProductVariant.product_id == Product.id,
                ProductVariant.sku.ilike(pattern, escape="\\"),
            )
        )
        stmt = stmt.where(
            or_(
                Product.name.ilike(pattern, escape="\\"),
                Product.code.ilike(pattern, escape="\\"),
                Product.slug.ilike(pattern, escape="\\"),
                sku_match,
            )
        )
    for code, raw in attr_filters:
        stmt = stmt.where(_matches_attribute(code, raw))

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.execute(
        stmt.order_by(Product.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    product_ids = [product.id for product, _name in rows]
    stats: dict[uuid.UUID, tuple[int, Decimal | None, Decimal | None]] = {}
    if product_ids:
        stat_rows = db.execute(
            select(
                ProductVariant.product_id,
                func.count(ProductVariant.id),
                func.min(ProductVariant.selling_price),
                func.max(ProductVariant.selling_price),
            )
            .where(ProductVariant.product_id.in_(product_ids))
            .group_by(ProductVariant.product_id)
        ).all()
        stats = {product_id: (count, low, high) for product_id, count, low, high in stat_rows}
    items = []
    for product, category_name in rows:
        count, low, high = stats.get(product.id, (0, None, None))
        items.append(
            ProductListItem(
                id=product.id,
                name=product.name,
                code=product.code,
                slug=product.slug,
                status=product.status,
                category_id=product.category_id,
                category_name=category_name,
                variant_count=count,
                selling_price_min=low,
                selling_price_max=high,
                updated_at=product.updated_at,
            )
        )
    return items, total
