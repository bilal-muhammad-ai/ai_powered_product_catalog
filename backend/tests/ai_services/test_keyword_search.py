from types import SimpleNamespace

import pytest

from app.services.ai_services.product_index.keyword import KeywordProductRetriever, keyword_search
from app.services.ai_services.product_index.retriever import RetrievedProduct


def _product(name: str, category: str = "Cement") -> RetrievedProduct:
    return RetrievedProduct(
        product_id=f"id-{name}",
        name=name,
        category_id="cat",
        category_name=category,
        selling_unit_id="unit",
        selling_unit_symbol="pc",
        selling_unit_name="Piece",
        score=0.2,
    )


CATALOGUE = [
    _product("DG Khan Cement PPC 43 — 50 kg bag"),
    _product("Lucky Cement OPC 53 — 20 kg bag"),
    _product("Lucky Cement OPC 53 — 50 kg bag"),
    _product("Maple Leaf Cement OPC 43 — 20 kg bag"),
    _product("Maple Leaf Cement OPC 43 — 50 kg bag"),
    _product("Wooden Paint Brush — 4 in", "Brushes"),
    _product("Wooden Paint Brush — 2 in", "Brushes"),
    _product("Wooden Paint Brush — 3 in", "Brushes"),
    _product("Steel Wire Brush — 2 in", "Brushes"),
    _product("Whitewash Brush — 7 in, dozen", "Brushes"),
    _product("GI Threaded Tee — 1 in", "Pipe Fittings"),
    _product("PPR Pressure Pipe PN20 — 1 in x 4 m", "Sanitary Pipes"),
]


def test_dg_cement_matches_only_the_named_brand():
    matches = keyword_search("DG cement", CATALOGUE)

    assert [product.name for product in matches] == ["DG Khan Cement PPC 43 — 50 kg bag"]
    assert matches[0].score == 1.0


def test_paintbrushes_match_each_paint_brush_size():
    matches = keyword_search("paintbrushes", CATALOGUE)

    assert [product.name for product in matches] == [
        "Wooden Paint Brush — 2 in",
        "Wooden Paint Brush — 3 in",
        "Wooden Paint Brush — 4 in",
    ]
    assert all(product.score == 1.0 for product in matches)


def test_missing_product_returns_nothing():
    assert keyword_search("toilet seat", CATALOGUE) == []


def test_blank_query_matches_nothing():
    assert keyword_search("   ", CATALOGUE) == []


def test_limit_keeps_the_first_matches_in_name_order():
    matches = keyword_search("cement", CATALOGUE, limit=2)

    assert [product.name for product in matches] == [
        "DG Khan Cement PPC 43 — 50 kg bag",
        "Lucky Cement OPC 53 — 20 kg bag",
    ]


def test_limit_must_be_positive():
    with pytest.raises(ValueError, match="limit must be at least 1"):
        keyword_search("cement", CATALOGUE, limit=0)


class PagedClient:
    def __init__(self, pages: list[tuple[list[SimpleNamespace], object | None]]) -> None:
        self.pages = pages
        self.calls: list[dict] = []

    def scroll(self, **kwargs):
        self.calls.append(kwargs)
        return self.pages[len(self.calls) - 1]


def _point(name: str) -> SimpleNamespace:
    return SimpleNamespace(
        payload={
            "product_id": f"id-{name}",
            "name": name,
            "category_id": "cat",
            "category_name": "Cement",
            "selling_unit_id": "unit",
            "selling_unit_symbol": "bag",
            "selling_unit_name": "Bag",
        }
    )


def test_keyword_retriever_scrolls_payloads_and_filters_by_name():
    client = PagedClient(
        [
            ([_point("Lucky Cement OPC 53 — 50 kg bag")], "next"),
            ([_point("DG Khan Cement PPC 43 — 50 kg bag"), _point("GI Threaded Tee — 1 in")], None),
        ]
    )
    retriever = KeywordProductRetriever(client, "catalogue_products")

    matches = retriever.retrieve("DG cement", limit=5)

    assert [call["collection_name"] for call in client.calls] == ["catalogue_products", "catalogue_products"]
    assert [call["offset"] for call in client.calls] == [None, "next"]
    assert client.calls[0]["with_payload"] is True
    assert client.calls[0]["with_vectors"] is False
    assert [product.name for product in matches] == ["DG Khan Cement PPC 43 — 50 kg bag"]


def test_keyword_retriever_does_not_scroll_a_blank_name():
    client = PagedClient([])
    retriever = KeywordProductRetriever(client, "catalogue_products")

    assert retriever.retrieve("   ") == []
    assert client.calls == []
