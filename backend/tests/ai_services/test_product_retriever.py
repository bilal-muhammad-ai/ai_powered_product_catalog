from types import SimpleNamespace

from qdrant_client.models import Fusion, FusionQuery

from app.services.ai_services.product_index.retriever import HybridProductRetriever, RetrievedProduct
from app.services.ai_services.product_index.store import (
    DENSE_VECTOR_NAME,
    SPARSE_VECTOR_NAME,
    VECTOR_SIZE,
    SparseEmbedding,
)


class RecordingEmbedder:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.texts.extend(texts)
        return [[1.0] + [0.0] * (VECTOR_SIZE - 1) for _text in texts]


class RecordingSparseEmbedder:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def embed(self, texts: list[str]) -> list[SparseEmbedding]:
        self.texts.extend(texts)
        return [SparseEmbedding(indices=[3], values=[0.5]) for _text in texts]


class FakeClient:
    def __init__(self, points: list[SimpleNamespace]) -> None:
        self.points = points
        self.calls: list[dict] = []

    def query_points(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(points=self.points)


def _retriever(
    client: FakeClient,
) -> tuple[HybridProductRetriever, RecordingEmbedder, RecordingSparseEmbedder]:
    embedder = RecordingEmbedder()
    sparse_embedder = RecordingSparseEmbedder()
    retriever = HybridProductRetriever(client, "catalogue_products", embedder, sparse_embedder)
    return retriever, embedder, sparse_embedder


def test_retrieve_fuses_dense_and_sparse_by_product_name():
    points = [
        SimpleNamespace(
            score=0.91,
            payload={
                "product_id": "id-1",
                "name": "Maple Leaf Cement",
                "category_id": "cat-1",
                "category_name": "Cement",
                "selling_unit_id": "unit-1",
                "selling_unit_symbol": "bag",
                "selling_unit_name": "Bag",
            },
        ),
        SimpleNamespace(score=0.42, payload={"product_id": "id-2", "name": "Lucky Cement"}),
    ]
    client = FakeClient(points)
    retriever, embedder, sparse_embedder = _retriever(client)

    results = retriever.retrieve("  Maple Leaf  ", limit=2)

    assert embedder.texts == ["query: Maple Leaf"]
    assert sparse_embedder.texts == ["Maple Leaf"]
    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["collection_name"] == "catalogue_products"
    assert call["limit"] == 2
    assert call["with_payload"] is True
    assert call["query"] == FusionQuery(fusion=Fusion.RRF)
    prefetches = call["prefetch"]
    assert [prefetch.using for prefetch in prefetches] == [DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME]
    assert prefetches[0].query[0] == 1.0
    assert len(prefetches[0].query) == VECTOR_SIZE
    assert prefetches[0].limit == 20
    assert list(prefetches[1].query.indices) == [3]
    assert list(prefetches[1].query.values) == [0.5]
    assert prefetches[1].limit == 20
    assert results == [
        RetrievedProduct(
            product_id="id-1",
            name="Maple Leaf Cement",
            category_id="cat-1",
            category_name="Cement",
            selling_unit_id="unit-1",
            selling_unit_symbol="bag",
            selling_unit_name="Bag",
            score=0.91,
        ),
        RetrievedProduct(
            product_id="id-2",
            name="Lucky Cement",
            category_id="",
            category_name="",
            selling_unit_id="",
            selling_unit_symbol="",
            selling_unit_name="",
            score=0.42,
        ),
    ]


def test_prefetch_grows_with_the_requested_limit():
    client = FakeClient([])
    retriever, _embedder, _sparse = _retriever(client)

    retriever.retrieve("Maple Leaf", limit=25)

    assert client.calls[0]["limit"] == 25
    assert [prefetch.limit for prefetch in client.calls[0]["prefetch"]] == [25, 25]


def test_blank_name_does_not_query():
    client = FakeClient([])
    retriever, embedder, sparse_embedder = _retriever(client)

    assert retriever.retrieve("   ") == []
    assert client.calls == []
    assert embedder.texts == []
    assert sparse_embedder.texts == []
