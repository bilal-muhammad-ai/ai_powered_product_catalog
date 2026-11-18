import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import CatalogueError
from app.models.product import Product
from app.models.variant import ProductVariant, VariantAttributeValue
from app.schemas.product import VariantDetail, VariantPatch
from app.services.products import _money, get_product, to_detail


def get_variant(db: Session, variant_id: uuid.UUID) -> ProductVariant:
    variant = db.scalar(
        select(ProductVariant)
        .join(Product, Product.id == ProductVariant.product_id)
        .where(ProductVariant.id == variant_id, Product.deleted_at.is_(None))
        .options(
            selectinload(ProductVariant.attribute_values).selectinload(VariantAttributeValue.attribute),
            selectinload(ProductVariant.product),
        )
    )
    if variant is None:
        raise CatalogueError("Variant not found", 404)
    return variant


def patch_variant(db: Session, variant: ProductVariant, data: VariantPatch) -> VariantDetail:
    changes = data.model_dump(exclude_unset=True)
    if "barcode" in changes:
        barcode = changes["barcode"]
        if barcode:
            clash = db.scalar(
                select(ProductVariant.id).where(
                    ProductVariant.barcode == barcode,
                    ProductVariant.id != variant.id,
                )
            )
            if clash is not None:
                raise CatalogueError("Barcode already exists", 409)
        variant.barcode = barcode
    if "cost_price" in changes and changes["cost_price"] is not None:
        variant.cost_price = _money(Decimal(changes["cost_price"]))
    if "selling_price" in changes and changes["selling_price"] is not None:
        variant.selling_price = _money(Decimal(changes["selling_price"]))
    if "is_active" in changes and changes["is_active"] is not None:
        variant.is_active = changes["is_active"]
    db.flush()
    product = get_product(db, variant.product_id)
    for item in to_detail(product).variants:
        if item.id == variant.id:
            return VariantDetail(product_id=product.id, **item.model_dump())
    raise CatalogueError("Variant not found", 404)
