from decimal import Decimal

from app.services.ai_services.order_agent import order_service
from app.services.ai_services.order_agent.schema import OrderItemDraft, StructuredOrder
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
