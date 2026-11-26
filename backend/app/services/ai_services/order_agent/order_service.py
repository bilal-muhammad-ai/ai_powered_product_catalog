from __future__ import annotations

import uuid
from decimal import Decimal
from functools import lru_cache
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.enums import ProductStatus
from app.models.product import Product
from app.services.ai_services.order_agent.schema import (
    MatchedOrder,
    MatchedOrderItem,
    ProductMatch,
    StructuredOrder,
)
from app.services.ai_services.product_index.embedder import FastEmbedSparseEmbedder, HuggingFaceEmbedder
from app.services.ai_services.product_index.keyword import KeywordProductRetriever
from app.services.ai_services.product_index.retriever import HybridProductRetriever, RetrievedProduct


class ProductNameRetriever(Protocol):
    def retrieve(self, product_name: str, limit: int = 5) -> list[RetrievedProduct]:
        """Return ranked catalogue products for one product name."""


@lru_cache
def get_product_retriever() -> HybridProductRetriever:
    settings = get_settings()
    return HybridProductRetriever.from_url(
        settings.qdrant_url,
        settings.qdrant_collection,
        HuggingFaceEmbedder(settings.hf_embedding_model, settings.hf_token),
        FastEmbedSparseEmbedder(settings.sparse_embedding_model),
    )


@lru_cache
def get_keyword_retriever() -> KeywordProductRetriever:
    settings = get_settings()
    return KeywordProductRetriever.from_url(settings.qdrant_url, settings.qdrant_collection)


def retrieve_order_products(order: StructuredOrder) -> MatchedOrder:
    """Search each item name in order and keep the quantity and unit beside the matches."""
    retriever = get_product_retriever()
    return _matched_order(order, retriever)


def retrieve_order_products_by_keyword(order: StructuredOrder) -> MatchedOrder:
    """Search each item name by keyword and keep the quantity and unit beside the matches."""
    retriever = get_keyword_retriever()
    return _matched_order(order, retriever)


def _matched_order(order: StructuredOrder, retriever: ProductNameRetriever) -> MatchedOrder:
    return MatchedOrder(
        intent=order.intent,
        items=[
            MatchedOrderItem(
                product_name=item.product_name,
                quantity=item.quantity,
                unit=item.unit,
                products=[_match(product) for product in retriever.retrieve(item.product_name or "")],
            )
            for item in order.items
        ],
    )


def _match(product: RetrievedProduct) -> ProductMatch:
    return ProductMatch(
        product_id=product.product_id,
        name=product.name,
        sku="",
        category_id=product.category_id,
        category_name=product.category_name,
        selling_unit_id=product.selling_unit_id,
        selling_unit_symbol=product.selling_unit_symbol,
        selling_unit_name=product.selling_unit_name,
        selling_price=Decimal("0"),
        score=product.score,
    )


def with_catalogue_details(db: Session, matched: MatchedOrder) -> MatchedOrder:
    """Replace retrieved match fields with the active catalogue row for each product id."""
    ids = {parsed for product_id in _product_ids(matched) if (parsed := _parse_id(product_id)) is not None}
    rows = _active_products(db, ids)
    return matched.model_copy(
        update={
            "items": [
                item.model_copy(update={"products": _catalogue_products(item.products, rows)})
                for item in matched.items
            ]
        }
    )


def _product_ids(matched: MatchedOrder) -> list[str]:
    return [product.product_id for item in matched.items for product in item.products]


def _parse_id(product_id: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(product_id)
    except ValueError:
        return None


def _active_products(db: Session, ids: set[uuid.UUID]) -> dict[uuid.UUID, Product]:
    if not ids:
        return {}
    stmt = (
        select(Product)
        .where(
            Product.id.in_(ids),
            Product.deleted_at.is_(None),
            Product.status == ProductStatus.active,
        )
        .options(selectinload(Product.category), selectinload(Product.selling_unit))
    )
    return {product.id: product for product in db.scalars(stmt)}


def _catalogue_products(matches: list[ProductMatch], rows: dict[uuid.UUID, Product]) -> list[ProductMatch]:
    products: list[ProductMatch] = []
    for match in matches:
        product_id = _parse_id(match.product_id)
        product = rows.get(product_id) if product_id is not None else None
        if product is None:
            continue
        products.append(
            ProductMatch(
                product_id=str(product.id),
                name=product.name,
                sku=product.sku,
                category_id=str(product.category_id),
                category_name=product.category.name,
                selling_unit_id=str(product.selling_unit_id),
                selling_unit_symbol=product.selling_unit.symbol,
                selling_unit_name=product.selling_unit.name,
                selling_price=product.selling_price,
                score=match.score,
            )
        )
    return products
