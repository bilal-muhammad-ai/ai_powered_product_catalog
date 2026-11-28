from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.enums import ProductStatus
from app.models.product import Product
from app.services.ai_services.product_index.documents import ProductDocument, build_document
from app.services.ai_services.product_index.embedder import (
    Embedder,
    FastEmbedSparseEmbedder,
    HuggingFaceEmbedder,
    SparseEmbedder,
)
from app.services.ai_services.product_index.store import (
    VECTOR_SIZE,
    ProductPoint,
    ProductStore,
    QdrantProductStore,
)

logger = logging.getLogger(__name__)

BATCH_SIZE = 32


@dataclass(frozen=True)
class IndexResult:
    upserted: int
    deleted: int


def load_active_products(db: Session) -> list[Product]:
    """Active products that are still in the catalogue."""
    stmt = (
        select(Product)
        .where(Product.status == ProductStatus.active, Product.deleted_at.is_(None))
        .options(selectinload(Product.category))
        .order_by(Product.name, Product.id)
    )
    return list(db.scalars(stmt))


def reindex(
    documents: list[ProductDocument],
    embedder: Embedder,
    sparse_embedder: SparseEmbedder,
    store: ProductStore,
) -> IndexResult:
    """Upsert the given products and delete Qdrant points that are not in that set."""
    store.ensure_collection()
    active_ids: list[str] = []
    for start in range(0, len(documents), BATCH_SIZE):
        batch = documents[start : start + BATCH_SIZE]
        passages = [document.passage for document in batch]
        vectors = embedder.embed(passages)
        sparse_vectors = sparse_embedder.embed(passages)
        if len(vectors) != len(batch) or len(sparse_vectors) != len(batch):
            raise RuntimeError("Embedding count does not match the product batch")
        for vector in vectors:
            if len(vector) != VECTOR_SIZE:
                raise RuntimeError(f"Expected {VECTOR_SIZE}-dimensional embeddings, got {len(vector)}")
        store.upsert(
            [
                ProductPoint(
                    product_id=str(document.product_id),
                    vector=vector,
                    sparse=sparse,
                    payload=document.payload,
                )
                for document, vector, sparse in zip(batch, vectors, sparse_vectors, strict=True)
            ]
        )
        active_ids.extend(str(document.product_id) for document in batch)

    stale = sorted(store.existing_ids() - set(active_ids))
    store.delete_ids(stale)
    return IndexResult(upserted=len(active_ids), deleted=len(stale))


def reindex_catalogue(
    db: Session,
    embedder: Embedder,
    sparse_embedder: SparseEmbedder,
    store: ProductStore,
) -> IndexResult:
    documents = [build_document(product) for product in load_active_products(db)]
    return reindex(documents, embedder, sparse_embedder, store)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = get_settings()
    embedder = HuggingFaceEmbedder(settings.hf_embedding_model, settings.hf_token)
    sparse_embedder = FastEmbedSparseEmbedder(settings.sparse_embedding_model)
    store = QdrantProductStore(settings.qdrant_url, settings.qdrant_collection)
    with SessionLocal() as db:
        result = reindex_catalogue(db, embedder, sparse_embedder, store)
    logger.info("indexed %s products, removed %s stale points", result.upserted, result.deleted)


if __name__ == "__main__":
    main()
