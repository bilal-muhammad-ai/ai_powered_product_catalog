import uuid
from datetime import datetime, timezone
from decimal import Decimal

from app.models.category import Category
from app.models.enums import ProductStatus, UnitType
from app.models.product import Product
from app.models.unit import Unit
from app.services.ai_services.order_agent import order_service
from app.services.ai_services.order_agent.schema import MatchedOrder, MatchedOrderItem, OrderItemDraft, ProductMatch, StructuredOrder
from app.services.ai_services.product_index.retriever import RetrievedProduct


class FakeRetriever:
    def __init__(self, by_name: dict[str, list[RetrievedProduct]]) -> None:
        self.by_name = by_name
        self.calls: list[str] = []

    def retrieve(self, product_name: str, limit: int = 5) -> list[RetrievedProduct]:
        self.calls.append(product_name)
        return list(self.by_name.get(product_name, []))


def _product(name: str, score: float) -> RetrievedProduct:
    return RetrievedProduct(
        product_id=f"id-{name}",
        name=name,
        category_id="cat",
        category_name="Cement",
        selling_unit_id="unit",
        selling_unit_symbol="bag",
        selling_unit_name="Bag",
        score=score,
    )


def test_each_named_item_is_searched_in_order(monkeypatch):
    lucky = _product("Lucky Cement OPC", 0.9)
    bajri = _product("Bajri", 0.8)
    retriever = FakeRetriever({"Lucky Cement": [lucky], "Bajri": [bajri]})
    monkeypatch.setattr(order_service, "get_product_retriever", lambda: retriever)
    order = StructuredOrder(
        items=[
            OrderItemDraft(product_name="Lucky Cement", quantity=Decimal("10"), unit="bag"),
            OrderItemDraft(product_name="Bajri", quantity=Decimal("30"), unit="ft"),
        ]
    )

    matched = order_service.retrieve_order_products(order)

    assert retriever.calls == ["Lucky Cement", "Bajri"]
    assert matched.intent == "create_order"
    assert [(item.product_name, item.quantity, item.unit) for item in matched.items] == [
        ("Lucky Cement", Decimal("10"), "bag"),
        ("Bajri", Decimal("30"), "ft"),
    ]
    assert [item.products[0].name for item in matched.items] == ["Lucky Cement OPC", "Bajri"]
    assert matched.items[0].products[0].score == 0.9
    assert matched.items[0].products[0].product_id == "id-Lucky Cement OPC"


def test_missing_product_name_returns_no_products(monkeypatch):
    retriever = FakeRetriever({})
    monkeypatch.setattr(order_service, "get_product_retriever", lambda: retriever)
    order = StructuredOrder(items=[OrderItemDraft(product_name=None, quantity=Decimal("2"), unit="bag")])

    matched = order_service.retrieve_order_products(order)

    assert retriever.calls == [""]
    assert matched.items[0].products == []
    assert matched.items[0].quantity == Decimal("2")
    assert matched.items[0].unit == "bag"


def test_keyword_order_search_uses_the_keyword_retriever(monkeypatch):
    cement = _product("DG Khan Cement", 1.0)
    retriever = FakeRetriever({"DG cement": [cement]})
    monkeypatch.setattr(order_service, "get_keyword_retriever", lambda: retriever)
    order = StructuredOrder(items=[OrderItemDraft(product_name="DG cement", quantity=Decimal("2"), unit="bag")])

    matched = order_service.retrieve_order_products_by_keyword(order)

    assert retriever.calls == ["DG cement"]
    assert matched.items[0].products[0].name == "DG Khan Cement"
    assert matched.items[0].quantity == Decimal("2")
    assert matched.items[0].unit == "bag"


def test_catalogue_details_replace_retrieved_fields(db):
    suffix = uuid.uuid4().hex[:8]
    unit = Unit(name="Bag", symbol=f"bag{suffix}", unit_type=UnitType.packaging)
    category = Category(name="OPC Cement", slug=f"opc-{suffix}", path=f"opc-{suffix}")
    db.add_all([unit, category])
    db.flush()
    active = Product(
        category_id=category.id,
        sku=f"CEM-{suffix}",
        name="Catalogue DG Cement",
        slug=f"cem-{suffix}",
        selling_unit_id=unit.id,
        selling_price=Decimal("1480.00"),
        status=ProductStatus.active,
    )
    draft = Product(
        category_id=category.id,
        sku=f"DR-{suffix}",
        name="Draft cement",
        slug=f"draft-{suffix}",
        selling_unit_id=unit.id,
        selling_price=Decimal("2.00"),
        status=ProductStatus.draft,
    )
    deleted = Product(
        category_id=category.id,
        sku=f"DL-{suffix}",
        name="Deleted cement",
        slug=f"deleted-{suffix}",
        selling_unit_id=unit.id,
        selling_price=Decimal("2.00"),
        status=ProductStatus.active,
        deleted_at=datetime.now(timezone.utc),
    )
    db.add_all([active, draft, deleted])
    db.flush()

    matched = MatchedOrder(
        items=[
            MatchedOrderItem(
                product_name="DG cement",
                quantity=Decimal("2"),
                unit="bag",
                products=[
                    ProductMatch(
                        product_id=str(active.id),
                        name="Payload cement name",
                        sku="PAYLOAD",
                        category_id="payload-cat",
                        category_name="Payload category",
                        selling_unit_id="payload-unit",
                        selling_unit_symbol="kg",
                        selling_unit_name="Kilogram",
                        selling_price=Decimal("1.00"),
                        score=0.7,
                    ),
                    ProductMatch(
                        product_id=str(draft.id),
                        name="Draft",
                        sku="DR",
                        category_id="payload-cat",
                        category_name="Payload category",
                        selling_unit_id="payload-unit",
                        selling_unit_symbol="kg",
                        selling_unit_name="Kilogram",
                        selling_price=Decimal("2.00"),
                        score=0.2,
                    ),
                    ProductMatch(
                        product_id=str(deleted.id),
                        name="Deleted",
                        sku="DL",
                        category_id="payload-cat",
                        category_name="Payload category",
                        selling_unit_id="payload-unit",
                        selling_unit_symbol="kg",
                        selling_unit_name="Kilogram",
                        selling_price=Decimal("3.00"),
                        score=0.1,
                    ),
                    ProductMatch(
                        product_id="not-a-uuid",
                        name="Missing",
                        sku="NO",
                        category_id="payload-cat",
                        category_name="Payload category",
                        selling_unit_id="payload-unit",
                        selling_unit_symbol="kg",
                        selling_unit_name="Kilogram",
                        selling_price=Decimal("4.00"),
                        score=0.1,
                    ),
                ],
            )
        ]
    )

    rebuilt = order_service.with_catalogue_details(db, matched)

    assert rebuilt.intent == "create_order"
    assert rebuilt.items[0].product_name == "DG cement"
    assert rebuilt.items[0].quantity == Decimal("2")
    assert rebuilt.items[0].unit == "bag"
    assert len(rebuilt.items[0].products) == 1
    product = rebuilt.items[0].products[0]
    assert product.product_id == str(active.id)
    assert product.name == "Catalogue DG Cement"
    assert product.sku == f"CEM-{suffix}"
    assert product.category_id == str(category.id)
    assert product.category_name == "OPC Cement"
    assert product.selling_unit_id == str(unit.id)
    assert product.selling_unit_symbol == unit.symbol
    assert product.selling_unit_name == "Bag"
    assert product.selling_price == Decimal("1480.00")
    assert product.score == 0.7
