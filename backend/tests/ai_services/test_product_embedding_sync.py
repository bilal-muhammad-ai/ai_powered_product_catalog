import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from app.background.product_tasks import sync_product_embedding
from app.models.category import Category
from app.models.enums import UnitType
from app.models.product import Product
from app.models.unit import Unit
from app.services.ai_services.product_index.documents import build_document
from app.services.ai_services.product_index.store import VECTOR_SIZE, ProductPoint, QdrantProductStore, SparseEmbedding


class FakeEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text))] + [0.0] * (VECTOR_SIZE - 1) for text in texts]


class FakeSparseEmbedder:
    def embed(self, texts: list[str]) -> list[SparseEmbedding]:
        return [SparseEmbedding(indices=[len(text)], values=[1.0]) for text in texts]


class FakeSyncStore:
    def __init__(self, matches: list[tuple[str, dict[str, str]]] | None = None, *, fail: bool = False) -> None:
        self.matches = matches or []
        self.fail = fail
        self.points: list[ProductPoint] = []
        self.ensured = False
        self.queried: str | None = None

    def ensure_collection(self) -> None:
        self.ensured = True

    def find_by_product_id(self, product_id: str) -> list[tuple[str, dict[str, str]]]:
        if self.fail:
            raise RuntimeError("qdrant unavailable")
        self.queried = product_id
        return list(self.matches)

    def upsert(self, points: list[ProductPoint]) -> None:
        self.points.extend(points)


class TrackingSession:
    def __init__(self, session: Session) -> None:
        self._session = session
        self.closed = False

    def scalar(self, statement):
        return self._session.scalar(statement)

    def close(self) -> None:
        self.closed = True


def _catalogue(db: Session) -> tuple[Product, TrackingSession]:
    suffix = uuid.uuid4().hex[:8]
    unit = Unit(name="Bag", symbol=f"bag{suffix}", unit_type=UnitType.packaging)
    category = Category(name="Cement", slug=f"cement-{suffix}", path=f"cement-{suffix}")
    db.add_all([unit, category])
    db.flush()
    product = Product(
        category_id=category.id,
        sku=f"CEM-{suffix}",
        name="OPC Cement 50 kg",
        slug=f"cem-{suffix}",
        selling_unit_id=unit.id,
        selling_price=Decimal("1100.00"),
    )
    db.add(product)
    db.flush()
    return product, TrackingSession(db)


def _patch_index(monkeypatch: pytest.MonkeyPatch, holder: TrackingSession, store: FakeSyncStore) -> None:
    monkeypatch.setattr("app.background.product_tasks.SessionLocal", lambda: holder)
    monkeypatch.setattr(
        "app.background.product_tasks._index_components",
        lambda: (FakeEmbedder(), FakeSparseEmbedder(), store),
    )


def test_sync_updates_existing_point_and_keeps_extra_metadata(db, monkeypatch):
    product, holder = _catalogue(db)
    legacy_id = "legacy-vector"
    store = FakeSyncStore(
        [
            (
                legacy_id,
                {
                    "product_id": str(product.id),
                    "source": "import",
                    "name": "Old name",
                    "category_id": "old-category",
                    "category_name": "Cement",
                    "selling_unit_id": "old-unit",
                    "selling_unit_symbol": "bag",
                    "selling_unit_name": "Bag",
                },
            )
        ]
    )
    _patch_index(monkeypatch, holder, store)

    sync_product_embedding(product.id)

    assert holder.closed
    assert store.ensured
    assert store.queried == str(product.id)
    assert [point.product_id for point in store.points] == [legacy_id]
    stored = store.points[0]
    assert stored.payload["source"] == "import"
    assert stored.payload["name"] == "OPC Cement 50 kg"
    assert stored.payload["product_id"] == str(product.id)
    assert "category_id" not in stored.payload
    assert "category_name" not in stored.payload
    assert "selling_unit_id" not in stored.payload
    assert "selling_unit_symbol" not in stored.payload
    assert "selling_unit_name" not in stored.payload
    assert stored.vector[0] == float(len(build_document(product).passage))
    assert stored.sparse.indices == [len(build_document(product).passage)]


def test_sync_inserts_when_no_embedding_exists(db, monkeypatch):
    product, holder = _catalogue(db)
    store = FakeSyncStore()
    _patch_index(monkeypatch, holder, store)

    sync_product_embedding(product.id)

    assert holder.closed
    assert [point.product_id for point in store.points] == [str(product.id)]
    assert store.points[0].payload == build_document(product).payload


def test_sync_logs_failure_and_leaves_the_product(db, monkeypatch, caplog):
    product, holder = _catalogue(db)
    store = FakeSyncStore(fail=True)
    _patch_index(monkeypatch, holder, store)

    with caplog.at_level(logging.ERROR):
        sync_product_embedding(product.id)

    assert holder.closed
    assert store.points == []
    assert db.get(Product, product.id) is not None
    assert f"failed to sync embedding for product {product.id}" in caplog.text


def test_sync_logs_missing_product_and_skips_the_index(db, monkeypatch, caplog):
    product, holder = _catalogue(db)
    product.deleted_at = datetime.now(timezone.utc)
    db.flush()
    store = FakeSyncStore()
    _patch_index(monkeypatch, holder, store)

    with caplog.at_level(logging.WARNING):
        sync_product_embedding(product.id)

    assert holder.closed
    assert store.ensured is False
    assert store.points == []
    assert f"product {product.id} not found for embedding sync" in caplog.text


def test_find_by_product_id_scrolls_with_a_metadata_filter(monkeypatch):
    pages = [
        (
            [SimpleNamespace(id="vector-1", payload={"product_id": "p1", "extra": "keep", "name": "Old"})],
            "next",
        ),
        (
            [SimpleNamespace(id=7, payload={"product_id": "p1", "note": None, "count": 2})],
            None,
        ),
    ]

    class FakeClient:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def scroll(self, **kwargs):
            self.calls.append(kwargs)
            return pages[len(self.calls) - 1]

    monkeypatch.setattr("qdrant_client.QdrantClient", lambda url: None)
    store = QdrantProductStore("http://localhost:6333", "catalogue_products")
    client = FakeClient()
    store._client = client

    found = store.find_by_product_id("p1")

    assert found == [
        ("vector-1", {"product_id": "p1", "extra": "keep", "name": "Old"}),
        ("7", {"product_id": "p1", "count": "2"}),
    ]
    assert len(client.calls) == 2
    assert client.calls[0]["offset"] is None
    assert client.calls[1]["offset"] == "next"
    assert client.calls[0]["with_payload"] is True
    assert client.calls[0]["with_vectors"] is False
    query_filter = client.calls[0]["scroll_filter"]
    assert query_filter.must[0].key == "product_id"
    assert query_filter.must[0].match.value == "p1"
