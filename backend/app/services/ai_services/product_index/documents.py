from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProductDocument:
    product_id: uuid.UUID
    passage: str
    payload: dict[str, str]


def passage_text(name: str, category_name: str) -> str:
    """English passage embedded for a product. The e5 model requires the passage prefix."""
    return f"passage: {name}\nCategory: {category_name})"


def build_document(product: Any) -> ProductDocument:
    """Build the embedding text and the payload used later to load the SQL row."""
    category = product.category
    passage = passage_text(product.name, category.name)
    return ProductDocument(
        product_id=product.id,
        passage=passage,
        payload={
            "product_id": str(product.id),
            "name": product.name,
        },
    )
