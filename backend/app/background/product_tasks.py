from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.product import Product
from app.services.ai_services.product_index.documents import build_document
from app.services.ai_services.product_index.embedder import (
    Embedder,
    FastEmbedSparseEmbedder,
    HuggingFaceEmbedder,
    SparseEmbedder,
)
from app.services.ai_services.product_index.store import (
    VECTOR_SIZE,
    ProductPoint,
    QdrantProductStore,
)

logger = logging.getLogger(__name__)

_embedder: Embedder | None = None
_sparse_embedder: SparseEmbedder | None = None
_store: QdrantProductStore | None = None


def _index_components() -> tuple[Embedder, SparseEmbedder, QdrantProductStore]:
    """Reuse the reindex models and collection for the life of this process."""
    global _embedder, _sparse_embedder, _store
    if _embedder is None or _sparse_embedder is None or _store is None:
        settings = get_settings()
        _embedder = HuggingFaceEmbedder(settings.hf_embedding_model, settings.hf_token)
        _sparse_embedder = FastEmbedSparseEmbedder(settings.sparse_embedding_model)
        _store = QdrantProductStore(settings.qdrant_url, settings.qdrant_collection)
    return _embedder, _sparse_embedder, _store


def sync_product_embedding(product_id: uuid.UUID) -> None:
    """Generate or update the vector for one product. Failures are logged only."""
    db = SessionLocal()
    try:
        _sync_product_embedding(db, product_id)
    except Exception:
        logger.exception("failed to sync embedding for product %s", product_id)
    finally:
        db.close()


def _sync_product_embedding(db: Session, product_id: uuid.UUID) -> None:
    product = db.scalar(
        select(Product)
        .where(Product.id == product_id, Product.deleted_at.is_(None))
        .options(selectinload(Product.category))
    )
    if product is None:
        logger.warning("product %s not found for embedding sync", product_id)
        return

    embedder, sparse_embedder, store = _index_components()
    store.ensure_collection()
    document = build_document(product)
    vectors = embedder.embed([document.passage])
    sparse_vectors = sparse_embedder.embed([document.passage])
    if len(vectors) != 1 or len(sparse_vectors) != 1:
        raise RuntimeError("Embedding count does not match the product")
    vector = vectors[0]
    sparse = sparse_vectors[0]
    if len(vector) != VECTOR_SIZE:
        raise RuntimeError(f"Expected {VECTOR_SIZE}-dimensional embeddings, got {len(vector)}")

    matches = store.find_by_product_id(str(product.id))
    if matches:
        points = [
            ProductPoint(
                product_id=point_id,
                vector=vector,
                sparse=sparse,
                payload={**existing_payload, **document.payload},
            )
            for point_id, existing_payload in matches
        ]
    else:
        points = [
            ProductPoint(
                product_id=str(document.product_id),
                vector=vector,
                sparse=sparse,
                payload=document.payload,
            )
        ]
    store.upsert(points)
