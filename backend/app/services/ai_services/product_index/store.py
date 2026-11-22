from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

VECTOR_SIZE = 384
DENSE_VECTOR_NAME = "product-dense-vector"
SPARSE_VECTOR_NAME = "product-sparse-vector"
_SCROLL_PAGE = 256


@dataclass(frozen=True)
class SparseEmbedding:
    indices: list[int]
    values: list[float]


@dataclass(frozen=True)
class ProductPoint:
    product_id: str
    vector: list[float]
    sparse: SparseEmbedding
    payload: dict[str, str]


class ProductStore(Protocol):
    def ensure_collection(self) -> None:
        """Create the named hybrid collection when it is missing."""

    def upsert(self, points: list[ProductPoint]) -> None:
        """Insert or replace points. Point id is the product UUID."""

    def existing_ids(self) -> set[str]:
        """Return every point id currently in the collection."""

    def delete_ids(self, ids: list[str]) -> None:
        """Remove the given points."""


class QdrantProductStore:
    def __init__(self, url: str, collection: str) -> None:
        from qdrant_client import QdrantClient

        self._client = QdrantClient(url=url)
        self._collection = collection

    def ensure_collection(self) -> None:
        from qdrant_client.models import Distance, Modifier, SparseVectorParams, VectorParams

        if self._client.collection_exists(self._collection):
            self._require_hybrid_schema()
            return
        self._client.create_collection(
            collection_name=self._collection,
            vectors_config={
                DENSE_VECTOR_NAME: VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            },
            sparse_vectors_config={
                SPARSE_VECTOR_NAME: SparseVectorParams(modifier=Modifier.IDF),
            },
        )

    def upsert(self, points: list[ProductPoint]) -> None:
        if not points:
            return
        from qdrant_client.models import PointStruct, SparseVector

        for point in points:
            if len(point.vector) != VECTOR_SIZE:
                raise RuntimeError(
                    f"Expected {VECTOR_SIZE}-dimensional embeddings, got {len(point.vector)}"
                )
            if len(point.sparse.indices) != len(point.sparse.values):
                raise RuntimeError("Sparse embedding indices and values must have the same length")
        self._client.upsert(
            collection_name=self._collection,
            points=[
                PointStruct(
                    id=point.product_id,
                    vector={
                        DENSE_VECTOR_NAME: point.vector,
                        SPARSE_VECTOR_NAME: SparseVector(
                            indices=point.sparse.indices,
                            values=point.sparse.values,
                        ),
                    },
                    payload=point.payload,
                )
                for point in points
            ],
        )

    def existing_ids(self) -> set[str]:
        ids: set[str] = set()
        offset = None
        while True:
            points, offset = self._client.scroll(
                collection_name=self._collection,
                limit=_SCROLL_PAGE,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )
            ids.update(str(point.id) for point in points)
            if offset is None:
                break
        return ids

    def delete_ids(self, ids: list[str]) -> None:
        if not ids:
            return
        from qdrant_client.models import PointIdsList

        for start in range(0, len(ids), _SCROLL_PAGE):
            self._client.delete(
                collection_name=self._collection,
                points_selector=PointIdsList(points=ids[start : start + _SCROLL_PAGE]),
            )

    def _require_hybrid_schema(self) -> None:
        params = self._client.get_collection(self._collection).config.params
        dense = _named_config(params.vectors, DENSE_VECTOR_NAME)
        size = getattr(dense, "size", None)
        raw_distance = getattr(dense, "distance", None)
        distance = getattr(raw_distance, "value", raw_distance)
        sparse = _named_config(params.sparse_vectors, SPARSE_VECTOR_NAME)
        raw_modifier = getattr(sparse, "modifier", None)
        modifier = getattr(raw_modifier, "value", raw_modifier)
        if size != VECTOR_SIZE or str(distance).lower() != "cosine" or str(modifier).lower() != "idf":
            raise RuntimeError(
                f"Collection {self._collection!r} must use cosine vector {DENSE_VECTOR_NAME!r} "
                f"of size {VECTOR_SIZE} and sparse vector {SPARSE_VECTOR_NAME!r} with the IDF modifier. "
                "Use a new collection name or delete the existing collection, then run the script again."
            )


def _named_config(configs: object, name: str) -> object | None:
    if isinstance(configs, dict):
        return configs.get(name)
    return None
