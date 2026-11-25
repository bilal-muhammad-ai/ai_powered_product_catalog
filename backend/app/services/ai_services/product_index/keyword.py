from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

from app.services.ai_services.product_index.retriever import RetrievedProduct

_DEFAULT_LIMIT = 5
_SCROLL_PAGE = 256
_TOKEN = re.compile(r"[a-z0-9]+")
_ES_SUFFIXES = ("ches", "shes", "sses", "xes", "zes")


class KeywordProductRetriever:
    """Find catalogue products by name using keywords only."""

    def __init__(self, client: Any, collection: str) -> None:
        self._client = client
        self._collection = collection

    @classmethod
    def from_url(cls, url: str, collection: str) -> KeywordProductRetriever:
        """Open a Qdrant client the same way the product store does."""
        from qdrant_client import QdrantClient

        return cls(QdrantClient(url=url), collection)

    def retrieve(self, product_name: str, limit: int = _DEFAULT_LIMIT) -> list[RetrievedProduct]:
        """Return products whose name contains every keyword. A blank name matches nothing."""
        name = product_name.strip()
        if not name:
            return []
        if limit < 1:
            raise ValueError("limit must be at least 1")
        return keyword_search(name, _scroll_products(self._client, self._collection), limit)


def keyword_search(
    product_name: str,
    products: list[RetrievedProduct],
    limit: int = _DEFAULT_LIMIT,
) -> list[RetrievedProduct]:
    """Keep products that contain every keyword in the name. Others are left out."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    query_tokens = _tokens(product_name)
    if not query_tokens:
        return []
    matched = [
        replace(product, score=1.0)
        for product in products
        if all(_token_in_name(token, _tokens(product.name)) for token in query_tokens)
    ]
    matched.sort(key=lambda product: (product.name.casefold(), product.product_id))
    return matched[:limit]


def _scroll_products(client: Any, collection: str) -> list[RetrievedProduct]:
    products: list[RetrievedProduct] = []
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=collection,
            limit=_SCROLL_PAGE,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        products.extend(_product(point) for point in points)
        if offset is None:
            break
    return products


def _product(point: Any) -> RetrievedProduct:
    payload = point.payload or {}
    return RetrievedProduct(
        product_id=_required(payload, "product_id"),
        name=_required(payload, "name"),
        category_id=_optional(payload, "category_id"),
        category_name=_optional(payload, "category_name"),
        selling_unit_id=_optional(payload, "selling_unit_id"),
        selling_unit_symbol=_optional(payload, "selling_unit_symbol"),
        selling_unit_name=_optional(payload, "selling_unit_name"),
        score=0.0,
    )


def _tokens(text: str) -> list[str]:
    return [_singular(token) for token in _TOKEN.findall(text.lower())]


def _singular(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith(_ES_SUFFIXES):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _token_in_name(token: str, name_tokens: list[str]) -> bool:
    if token in name_tokens:
        return True
    for start in range(len(name_tokens)):
        joined = ""
        for index in range(start, len(name_tokens)):
            joined += name_tokens[index]
            if joined == token:
                return True
            if len(joined) > len(token):
                break
    return False


def _required(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if value is None or not str(value).strip():
        raise RuntimeError(f"Retrieved point is missing {key}")
    return str(value)


def _optional(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if value is None:
        return ""
    return str(value)
