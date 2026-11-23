from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.services.ai_services.product_index.embedder import Embedder, SparseEmbedder
from app.services.ai_services.product_index.store import (
    DENSE_VECTOR_NAME,
    SPARSE_VECTOR_NAME,
    VECTOR_SIZE,
    SparseEmbedding,
)

_DEFAULT_LIMIT = 5
_DEFAULT_PREFETCH = 20


@dataclass(frozen=True)
class RetrievedProduct:
    product_id: str
    name: str
    category_id: str
    category_name: str
    selling_unit_id: str
    selling_unit_symbol: str
    selling_unit_name: str
    score: float


class _PointQuery(Protocol):
    def query_points(self, **kwargs: Any) -> Any:
        """Run one Qdrant query and return a response with points."""


class HybridProductRetriever:
    """Find catalogue products by name with dense and sparse vectors fused by RRF."""

    def __init__(
        self,
        client: _PointQuery,
        collection: str,
        embedder: Embedder,
        sparse_embedder: SparseEmbedder,
        *,
        prefetch_limit: int = _DEFAULT_PREFETCH,
    ) -> None:
        self._client = client
        self._collection = collection
        self._embedder = embedder
        self._sparse_embedder = sparse_embedder
        self._prefetch_limit = prefetch_limit

    @classmethod
    def from_url(
        cls,
        url: str,
        collection: str,
        embedder: Embedder,
        sparse_embedder: SparseEmbedder,
        *,
        prefetch_limit: int = _DEFAULT_PREFETCH,
    ) -> HybridProductRetriever:
        """Open a Qdrant client the same way the product store does."""
        from qdrant_client import QdrantClient

        return cls(
            QdrantClient(url=url),
            collection,
            embedder,
            sparse_embedder,
            prefetch_limit=prefetch_limit,
        )

    def retrieve(self, product_name: str, limit: int = _DEFAULT_LIMIT) -> list[RetrievedProduct]:
        """Return the closest products for one product name. A blank name matches nothing."""
        name = product_name.strip()
        if not name:
            return []
        if limit < 1:
            raise ValueError("limit must be at least 1")
        dense = _one_dense(self._embedder.embed([f"query: {name}"]))
        sparse = _one_sparse(self._sparse_embedder.embed([name]))
        response = self._client.query_points(
            collection_name=self._collection,
            prefetch=_prefetches(dense, sparse, max(limit, self._prefetch_limit)),
            query=_rrf(),
            limit=limit,
            with_payload=True,
        )
        return [_retrieved(point) for point in response.points]


def _one_dense(vectors: list[list[float]]) -> list[float]:
    if len(vectors) != 1:
        raise RuntimeError("Embedding count does not match the product name")
    vector = vectors[0]
    if len(vector) != VECTOR_SIZE:
        raise RuntimeError(f"Expected {VECTOR_SIZE}-dimensional embeddings, got {len(vector)}")
    return vector


def _one_sparse(vectors: list[SparseEmbedding]) -> SparseEmbedding:
    if len(vectors) != 1:
        raise RuntimeError("Sparse embedding count does not match the product name")
    sparse = vectors[0]
    if len(sparse.indices) != len(sparse.values):
        raise RuntimeError("Sparse embedding indices and values must have the same length")
    return sparse


def _prefetches(dense: list[float], sparse: SparseEmbedding, limit: int) -> list[Any]:
    from qdrant_client.models import Prefetch, SparseVector

    return [
        Prefetch(query=dense, using=DENSE_VECTOR_NAME, limit=limit),
        Prefetch(
            query=SparseVector(indices=sparse.indices, values=sparse.values),
            using=SPARSE_VECTOR_NAME,
            limit=limit,
        ),
    ]


def _rrf() -> Any:
    from qdrant_client.models import Fusion, FusionQuery

    return FusionQuery(fusion=Fusion.RRF)


def _retrieved(point: Any) -> RetrievedProduct:
    payload = point.payload or {}
    return RetrievedProduct(
        product_id=_required(payload, "product_id"),
        name=_required(payload, "name"),
        category_id=_optional(payload, "category_id"),
        category_name=_optional(payload, "category_name"),
        selling_unit_id=_optional(payload, "selling_unit_id"),
        selling_unit_symbol=_optional(payload, "selling_unit_symbol"),
        selling_unit_name=_optional(payload, "selling_unit_name"),
        score=float(point.score),
    )


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
