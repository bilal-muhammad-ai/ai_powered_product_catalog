from __future__ import annotations

from functools import lru_cache
from typing import Protocol

from app.core.config import get_settings
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
        category_id=product.category_id,
        category_name=product.category_name,
        selling_unit_id=product.selling_unit_id,
        selling_unit_symbol=product.selling_unit_symbol,
        selling_unit_name=product.selling_unit_name,
        score=product.score,
    )
