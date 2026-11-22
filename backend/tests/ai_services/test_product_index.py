import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.api.v1.ai.product_ingestion import get_embedder, get_sparse_embedder, get_store
from app.main import app
from app.models.category import Category
from app.models.enums import ProductStatus, UnitType
from app.models.product import Product
from app.models.unit import Unit
from app.services.ai_services.product_index.documents import build_document, passage_text
from app.services.ai_services.product_index.reindex import IndexResult, load_active_products, reindex, reindex_catalogue
from app.services.ai_services.product_index.store import VECTOR_SIZE, ProductPoint, SparseEmbedding


class FakeEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(index)] + [0.0] * (VECTOR_SIZE - 1) for index, _text in enumerate(texts, start=1)]


class FakeSparseEmbedder:
    def embed(self, texts: list[str]) -> list[SparseEmbedding]:
        return [
            SparseEmbedding(indices=[index], values=[float(index)])
            for index, _text in enumerate(texts, start=1)
        ]


class FakeStore:
    def __init__(self, existing_ids: set[str] | None = None) -> None:
        self.points = {
            product_id: ProductPoint(
                product_id=product_id,
                vector=[],
                sparse=SparseEmbedding(indices=[], values=[]),
                payload={},
            )
            for product_id in (existing_ids or set())
        }
        self.ensured = False

    def ensure_collection(self) -> None:
        self.ensured = True

    def upsert(self, points: list[ProductPoint]) -> None:
        for point in points:
            self.points[point.product_id] = point

    def existing_ids(self) -> set[str]:
        return set(self.points)

    def delete_ids(self, ids: list[str]) -> None:
        for product_id in ids:
            self.points.pop(product_id, None)


def _product_stub(**overrides):
    product_id = overrides.pop("id", uuid.uuid4())
    category_id = overrides.pop("category_id", uuid.uuid4())
    unit_id = overrides.pop("selling_unit_id", uuid.uuid4())
    values = {
        "id": product_id,
        "name": "Maple Leaf Cement OPC 43 — 50 kg bag",
        "sku": "CEM-ML-OPC43-50",
        "category_id": category_id,
        "selling_unit_id": unit_id,
        "status": ProductStatus.active,
        "selling_price": Decimal("1480.00"),
        "cost_price": Decimal("1310.00"),
        "category": SimpleNamespace(name="Cement"),
        "selling_unit": SimpleNamespace(name="Bag", symbol="bag"),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_passage_includes_name_category_and_unit_only():
    text = passage_text("Maple Leaf Cement OPC 43 — 50 kg bag", "Cement", "Bag", "bag")

    assert text == "passage: Maple Leaf Cement OPC 43 — 50 kg bag\nCategory: Cement\nUnit: Bag (bag)"
    document = build_document(_product_stub())
    assert document.passage == text
    assert "1480" not in document.passage
    assert "1310" not in document.passage
    assert "selling_price" not in document.payload
    assert "cost_price" not in document.payload
    assert document.payload["category_name"] == "Cement"
    assert document.payload["selling_unit_symbol"] == "bag"
    assert document.payload["selling_unit_name"] == "Bag"


def test_reindex_upserts_active_products_and_drops_stale_ids():
    document = build_document(_product_stub())
    store = FakeStore({str(document.product_id), "stale-id"})

    result = reindex([document], FakeEmbedder(), FakeSparseEmbedder(), store)

    assert result == IndexResult(upserted=1, deleted=1)
    assert store.ensured
    assert set(store.points) == {str(document.product_id)}
    stored = store.points[str(document.product_id)]
    assert stored.payload["name"] == "Maple Leaf Cement OPC 43 — 50 kg bag"
    assert stored.vector[0] == 1.0
    assert len(stored.vector) == VECTOR_SIZE
    assert stored.sparse.indices == [1]
    assert stored.sparse.values == [1.0]


def test_reindex_removes_every_point_when_no_products_remain():
    store = FakeStore({"gone"})

    result = reindex([], FakeEmbedder(), FakeSparseEmbedder(), store)

    assert result == IndexResult(upserted=0, deleted=1)
    assert store.points == {}


def test_reindex_catalogue_indexes_only_active_products(db):
    suffix = uuid.uuid4().hex[:8]
    unit = Unit(name="Bag", symbol=f"bag{suffix}", unit_type=UnitType.packaging)
    category = Category(name="Cement", slug=f"cement-{suffix}", path=f"cement-{suffix}")
    db.add_all([unit, category])
    db.flush()

    def add_product(name: str, sku: str, status: ProductStatus, *, deleted: bool = False) -> Product:
        product = Product(
            category_id=category.id,
            sku=sku,
            name=name,
            slug=sku.lower(),
            selling_unit_id=unit.id,
            cost_price=Decimal("1310.00"),
            selling_price=Decimal("1480.00"),
            status=status,
            deleted_at=datetime.now(timezone.utc) if deleted else None,
        )
        db.add(product)
        return product

    active = add_product("Lucky Cement OPC 53 — 50 kg bag", f"CEM-LC-{suffix}", ProductStatus.active)
    draft = add_product("Draft cement", f"CEM-DR-{suffix}", ProductStatus.draft)
    deleted = add_product("Retired cement", f"CEM-DL-{suffix}", ProductStatus.active, deleted=True)
    db.flush()

    store = FakeStore({str(active.id), "no-longer-active"})
    result = reindex_catalogue(db, FakeEmbedder(), FakeSparseEmbedder(), store)

    loaded_ids = {product.id for product in load_active_products(db)}
    assert active.id in loaded_ids
    assert draft.id not in loaded_ids
    assert deleted.id not in loaded_ids
    assert result.upserted == len(loaded_ids)
    assert str(active.id) in store.points
    assert str(draft.id) not in store.points
    assert str(deleted.id) not in store.points
    assert "no-longer-active" not in store.points
    payload = store.points[str(active.id)].payload
    assert payload["name"] == "Lucky Cement OPC 53 — 50 kg bag"
    assert "1480" not in " ".join(payload.values())


def test_product_ingestion_endpoint_indexes_with_injected_dependencies(client, db):
    suffix = uuid.uuid4().hex[:8]
    unit = Unit(name="Bag", symbol=f"ing{suffix}", unit_type=UnitType.packaging)
    category = Category(name="Cement", slug=f"ingest-{suffix}", path=f"ingest-{suffix}")
    db.add_all([unit, category])
    db.flush()
    active = Product(
        category_id=category.id,
        sku=f"CEM-IN-{suffix}",
        name="Lucky Cement OPC 53 — 50 kg bag",
        slug=f"cem-in-{suffix}",
        selling_unit_id=unit.id,
        cost_price=Decimal("1310.00"),
        selling_price=Decimal("1480.00"),
        status=ProductStatus.active,
    )
    db.add(active)
    db.flush()

    store = FakeStore({"stale-id"})
    app.dependency_overrides[get_embedder] = lambda: FakeEmbedder()
    app.dependency_overrides[get_sparse_embedder] = lambda: FakeSparseEmbedder()
    app.dependency_overrides[get_store] = lambda: store

    response = client.post("/api/v1/ai/product_ingestion")

    assert response.status_code == 200, response.text
    body = response.json()
    loaded_ids = {product.id for product in load_active_products(db)}
    assert active.id in loaded_ids
    assert body == {"upserted": len(loaded_ids), "deleted": 1}
    assert str(active.id) in store.points
    assert "stale-id" not in store.points
    stored = store.points[str(active.id)]
    assert "1480" not in " ".join(stored.payload.values())
    assert stored.sparse.indices == [1]
    assert stored.vector[0] == 1.0
