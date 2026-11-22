from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.services.ai_services.product_index.embedder import FastEmbedSparseEmbedder, HuggingFaceEmbedder
from app.services.ai_services.product_index.reindex import reindex_catalogue
from app.services.ai_services.product_index.store import QdrantProductStore

router = APIRouter(prefix="/ai", tags=["ai"])


class ProductIngestionResult(BaseModel):
    upserted: int
    deleted: int


def get_embedder() -> HuggingFaceEmbedder:
    settings = get_settings()
    return HuggingFaceEmbedder(settings.hf_embedding_model, settings.hf_token)


def get_sparse_embedder() -> FastEmbedSparseEmbedder:
    settings = get_settings()
    return FastEmbedSparseEmbedder(settings.sparse_embedding_model)


def get_store() -> QdrantProductStore:
    settings = get_settings()
    return QdrantProductStore(settings.qdrant_url, settings.qdrant_collection)


@router.post("/product_ingestion", response_model=ProductIngestionResult)
def ingest_products(
    db: Session = Depends(get_db),
    embedder=Depends(get_embedder),
    sparse_embedder=Depends(get_sparse_embedder),
    store=Depends(get_store),
) -> ProductIngestionResult:
    result = reindex_catalogue(db, embedder, sparse_embedder, store)
    return ProductIngestionResult(upserted=result.upserted, deleted=result.deleted)
