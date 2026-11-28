import uuid
from datetime import date
from decimal import Decimal

from app.services.order.calculation import order_amounts
from app.services.unit_conversion import sync_unit_conversions
from app.models.order.enums import DiscountType


def _unit(client, name, symbol, unit_type):
    response = client.post("/api/v1/units", json={"name": name, "symbol": symbol, "unit_type": unit_type})
    assert response.status_code == 201, response.text
    return response.json()


def _product(client, unit_id, name, sku, **extra):
    category = client.post("/api/v1/categories", json={"name": f"Cat {sku}"}).json()
    payload = {
        "category_id": category["id"],
        "name": name,
        "sku": sku,
        "selling_unit_id": unit_id,
        "selling_price": "1100",
        "status": "active",
        "attribute_values": [],
    }
    payload.update(extra)
    response = client.post("/api/v1/products", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _stock(client, product_id, unit_id, quantity="20", cost="100"):
    response = client.post(
        "/api/v1/inventory/opening-stock",
        json={
            "transaction_date": "2026-11-19",
            "post": True,
            "items": [{"product_id": product_id, "unit_id": unit_id, "quantity": quantity, "unit_cost": cost}],
        },
    )
    assert response.status_code == 201, response.text


def _order(client, product_id, unit_id, **extra):
    payload = {
        "order_date": "2026-11-19",
        "discount_type": "AMOUNT",
        "discount_value": "0",
        "items": [
            {
                "product_id": product_id,
                "unit_id": unit_id,
                "quantity": "2",
                "unit_price": "1100",
                "discount_type": "AMOUNT",
                "discount_value": "0",
            }
        ],
    }
    payload.update(extra)
    return client.post("/api/v1/orders", json=payload)


def test_order_calculation_discounts_and_rounding():
    amounts = order_amounts(
        [
            (Decimal("2"), Decimal("1100"), DiscountType.amount, Decimal("100")),
            (Decimal("1.5"), Decimal("80"), DiscountType.percent, Decimal("10")),
        ],
        DiscountType.percent,
        Decimal("5"),
    )
    assert amounts.lines[0].subtotal == Decimal("2200.00")
    assert amounts.lines[0].discount_amount == Decimal("100.00")
    assert amounts.lines[0].total == Decimal("2100.00")
    assert amounts.lines[1].subtotal == Decimal("120.00")
    assert amounts.lines[1].discount_amount == Decimal("12.00")
    assert amounts.subtotal == Decimal("2320.00")
    assert amounts.item_discount_total == Decimal("112.00")
    assert amounts.order_discount_amount == Decimal("110.40")
    assert amounts.grand_total == Decimal("2097.60")


def test_orders_are_open_without_credentials(client):
    response = client.get("/api/v1/orders")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_draft_totals_edit_and_snapshots(client):
    bag = _unit(client, "Bag", f"bag-{uuid.uuid4().hex[:6]}", "packaging")
    product = _product(client, bag["id"], "Maple Leaf 50kg", f"CEM-{uuid.uuid4().hex[:6]}", selling_price="1100")
    created = _order(
        client,
        product["id"],
        bag["id"],
        items=[
            {
                "product_id": product["id"],
                "unit_id": bag["id"],
                "quantity": "2",
                "unit_price": "1000",
                "discount_type": "PERCENT",
                "discount_value": "10",
            }
        ],
        discount_type="AMOUNT",
        discount_value="50",
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "DRAFT"
    assert body["order_number"].startswith("ORD-2026-")
    assert body["subtotal"] == "2000.00"
    assert body["item_discount_total"] == "200.00"
    assert body["order_discount_amount"] == "50.00"
    assert body["grand_total"] == "1750.00"
    assert body["items"][0]["product_name_snapshot"] == "Maple Leaf 50kg"
    assert body["items"][0]["unit_name_snapshot"] == bag["symbol"]
    order_id = body["id"]
    item_id = body["items"][0]["id"]

    updated = client.put(
        f"/api/v1/orders/{order_id}/items/{item_id}",
        json={
            "product_id": product["id"],
            "unit_id": bag["id"],
            "quantity": "3",
            "unit_price": "1000",
            "discount_type": "AMOUNT",
            "discount_value": "0",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["grand_total"] == "2950.00"

    renamed = client.patch(
        f"/api/v1/products/{product['id']}",
        json={
            "category_id": product["category_id"],
            "name": "Renamed cement",
            "sku": product["sku"],
            "selling_unit_id": bag["id"],
            "selling_price": "1500",
            "status": "active",
            "attribute_values": [],
        },
    )
    assert renamed.status_code == 200, renamed.text
    stored = client.get(f"/api/v1/orders/{order_id}").json()
    assert stored["items"][0]["product_name_snapshot"] == "Maple Leaf 50kg"
    assert stored["items"][0]["unit_price"] == "1000.00"
    stock = client.get(f"/api/v1/inventory/{product['id']}").json()
    assert Decimal(stock["quantity_on_hand"]) == Decimal("0")


def test_confirm_issues_stock_and_cancel_reverses_it(client):
    bag = _unit(client, "Bag", f"bag-{uuid.uuid4().hex[:6]}", "packaging")
    product = _product(client, bag["id"], "Cement", f"CEM-{uuid.uuid4().hex[:6]}")
    _stock(client, product["id"], bag["id"], "10", "100")
    created = _order(client, product["id"], bag["id"])
    order_id = created.json()["id"]
    confirmed = client.post(f"/api/v1/orders/{order_id}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "CONFIRMED"
    assert confirmed.json()["inventory_transaction_number"].startswith("INV-")
    assert client.get(f"/api/v1/inventory/{product['id']}").json()["quantity_on_hand"] == "8.0000"
    again = client.post(f"/api/v1/orders/{order_id}/confirm")
    assert again.status_code == 409
    assert client.get(f"/api/v1/inventory/{product['id']}").json()["quantity_on_hand"] == "8.0000"

    cancelled = client.post(f"/api/v1/orders/{order_id}/cancel")
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "CANCELLED"
    assert client.get(f"/api/v1/inventory/{product['id']}").json()["quantity_on_hand"] == "10.0000"
    second = client.post(f"/api/v1/orders/{order_id}/cancel")
    assert second.status_code == 409


def test_confirm_converts_units_and_rejects_invalid_lines(client, db):
    bag = _unit(client, "Bag", f"bag-{uuid.uuid4().hex[:6]}", "packaging")
    kg = _unit(client, "Kilogram", "kg", "weight")
    ton = _unit(client, "Ton", "ton", "weight")
    sync_unit_conversions(db)
    product = _product(
        client,
        bag["id"],
        "Bagged cement",
        f"BAG-{uuid.uuid4().hex[:6]}",
        net_quantity="50",
        net_quantity_unit_id=kg["id"],
    )
    _stock(client, product["id"], bag["id"], "10", "100")
    created = _order(
        client,
        product["id"],
        ton["id"],
        items=[
            {
                "product_id": product["id"],
                "unit_id": ton["id"],
                "quantity": "0.5",
                "unit_price": "24000",
                "discount_type": "AMOUNT",
                "discount_value": "0",
            }
        ],
    )
    assert created.status_code == 201, created.text
    confirmed = client.post(f"/api/v1/orders/{created.json()['id']}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    assert client.get(f"/api/v1/inventory/{product['id']}").json()["quantity_on_hand"] == "0.0000"

    piece = _unit(client, "Piece", f"pc-{uuid.uuid4().hex[:4]}", "count")
    other = _product(client, piece["id"], "Rod", f"ROD-{uuid.uuid4().hex[:6]}")
    invalid = _order(client, other["id"], bag["id"])
    assert invalid.status_code == 422
    inactive = client.post(
        "/api/v1/orders",
        json={
            "order_date": "2026-11-19",
            "items": [
                {
                    "product_id": str(uuid.uuid4()),
                    "unit_id": piece["id"],
                    "quantity": "1",
                    "unit_price": "10",
                }
            ],
        },
    )
    assert inactive.status_code == 404
    negative = _order(
        client,
        other["id"],
        piece["id"],
        items=[
            {
                "product_id": other["id"],
                "unit_id": piece["id"],
                "quantity": "-1",
                "unit_price": "10",
                "discount_type": "AMOUNT",
                "discount_value": "0",
            }
        ],
    )
    assert negative.status_code == 422
    over_discount = _order(
        client,
        other["id"],
        piece["id"],
        items=[
            {
                "product_id": other["id"],
                "unit_id": piece["id"],
                "quantity": "1",
                "unit_price": "10",
                "discount_type": "AMOUNT",
                "discount_value": "11",
            }
        ],
    )
    assert over_discount.status_code == 422


def test_insufficient_stock_leaves_the_draft(client):
    bag = _unit(client, "Bag", f"bag-{uuid.uuid4().hex[:6]}", "packaging")
    product = _product(client, bag["id"], "Sand", f"SAND-{uuid.uuid4().hex[:6]}")
    _stock(client, product["id"], bag["id"], "2", "50")
    created = _order(
        client,
        product["id"],
        bag["id"],
        items=[
            {
                "product_id": product["id"],
                "unit_id": bag["id"],
                "quantity": "5",
                "unit_price": "80",
                "discount_type": "AMOUNT",
                "discount_value": "0",
            }
        ],
    )
    order_id = created.json()["id"]
    refused = client.post(f"/api/v1/orders/{order_id}/confirm")
    assert refused.status_code == 422
    assert client.get(f"/api/v1/orders/{order_id}").json()["status"] == "DRAFT"
    assert client.get(f"/api/v1/inventory/{product['id']}").json()["quantity_on_hand"] == "2.0000"


def test_delete_draft_add_and_remove_items_and_filters(client):
    bag = _unit(client, "Bag", f"bag-{uuid.uuid4().hex[:6]}", "packaging")
    first = _product(client, bag["id"], "Cement", f"CEM-{uuid.uuid4().hex[:6]}")
    second = _product(client, bag["id"], "Sand", f"SAND-{uuid.uuid4().hex[:6]}")
    created = _order(client, first["id"], bag["id"])
    order_id = created.json()["id"]
    added = client.post(
        f"/api/v1/orders/{order_id}/items",
        json={
            "product_id": second["id"],
            "unit_id": bag["id"],
            "quantity": "4",
            "unit_price": "50",
            "discount_type": "AMOUNT",
            "discount_value": "0",
        },
    )
    assert added.status_code == 201, added.text
    assert added.json()["item_count"] == 2
    assert added.json()["grand_total"] == "2400.00"
    removed = client.delete(f"/api/v1/orders/{order_id}/items/{added.json()['items'][1]['id']}")
    assert removed.status_code == 200, removed.text
    assert removed.json()["item_count"] == 1

    listed = client.get("/api/v1/orders", params={"q": created.json()["order_number"], "status": "DRAFT", "date_from": "2026-11-19", "date_to": "2026-11-19"})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    deleted = client.delete(f"/api/v1/orders/{order_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/orders/{order_id}").status_code == 404


def test_quantity_unit_price_and_stock_conversion(client):
    piece = _unit(client, "Piece", f"pc-{uuid.uuid4().hex[:6]}", "count")
    foot = _unit(client, "Feet", f"ft-{uuid.uuid4().hex[:6]}", "length")
    pipe = _product(
        client,
        piece["id"],
        "Soil pipe",
        f"PIPE-{uuid.uuid4().hex[:6]}",
        net_quantity="20",
        net_quantity_unit_id=foot["id"],
        selling_price="500",
        quantity_unit_price="25",
    )
    assert pipe["quantity_unit_price"] == "25.00"
    assert pipe["selling_price"] == "500.00"
    missing = client.post(
        "/api/v1/products",
        json={
            "category_id": pipe["category_id"],
            "name": "Open pipe",
            "sku": f"OPEN-{uuid.uuid4().hex[:6]}",
            "selling_unit_id": piece["id"],
            "net_quantity_unit_id": foot["id"],
            "selling_price": "2",
            "status": "active",
            "attribute_values": [],
        },
    )
    assert missing.status_code == 422

    _stock(client, pipe["id"], piece["id"], "10", "400")
    pieces = _order(
        client,
        pipe["id"],
        piece["id"],
        items=[
            {
                "product_id": pipe["id"],
                "unit_id": piece["id"],
                "quantity": "2",
                "unit_price": "500",
                "discount_type": "AMOUNT",
                "discount_value": "0",
            }
        ],
    )
    assert pieces.status_code == 201, pieces.text
    assert pieces.json()["items"][0]["subtotal"] == "1000.00"
    confirmed_pieces = client.post(f"/api/v1/orders/{pieces.json()['id']}/confirm")
    assert confirmed_pieces.status_code == 200, confirmed_pieces.text
    assert client.get(f"/api/v1/inventory/{pipe['id']}").json()["quantity_on_hand"] == "8.0000"

    feet = _order(
        client,
        pipe["id"],
        foot["id"],
        discount_type="AMOUNT",
        discount_value="10",
        items=[
            {
                "product_id": pipe["id"],
                "unit_id": foot["id"],
                "quantity": "7",
                "unit_price": "25",
                "discount_type": "AMOUNT",
                "discount_value": "5",
            }
        ],
    )
    assert feet.status_code == 201, feet.text
    body = feet.json()
    assert body["items"][0]["subtotal"] == "175.00"
    assert body["items"][0]["total"] == "170.00"
    assert body["grand_total"] == "160.00"
    confirmed_feet = client.post(f"/api/v1/orders/{body['id']}/confirm")
    assert confirmed_feet.status_code == 200, confirmed_feet.text
    movement = client.get(f"/api/v1/inventory/transactions/{confirmed_feet.json()['inventory_transaction_id']}")
    assert movement.status_code == 200, movement.text
    line = movement.json()["items"][0]
    assert line["unit_id"] == foot["id"]
    assert Decimal(line["quantity"]) == Decimal("7")
    assert Decimal(line["quantity_delta"]) == Decimal("-0.35")
    assert client.get(f"/api/v1/inventory/{pipe['id']}").json()["quantity_on_hand"] == "7.6500"

    short = _order(
        client,
        pipe["id"],
        piece["id"],
        items=[
            {
                "product_id": pipe["id"],
                "unit_id": piece["id"],
                "quantity": "8",
                "unit_price": "500",
                "discount_type": "AMOUNT",
                "discount_value": "0",
            },
            {
                "product_id": pipe["id"],
                "unit_id": foot["id"],
                "quantity": "7",
                "unit_price": "25",
                "discount_type": "AMOUNT",
                "discount_value": "0",
            },
        ],
    )
    assert short.status_code == 201, short.text
    refused = client.post(f"/api/v1/orders/{short.json()['id']}/confirm")
    assert refused.status_code == 422
    assert client.get(f"/api/v1/inventory/{pipe['id']}").json()["quantity_on_hand"] == "7.6500"

    cancelled = client.post(f"/api/v1/orders/{body['id']}/cancel")
    assert cancelled.status_code == 200, cancelled.text
    assert client.get(f"/api/v1/inventory/{pipe['id']}").json()["quantity_on_hand"] == "8.0000"

    box_unit = _unit(client, "Box", f"box-{uuid.uuid4().hex[:6]}", "packaging")
    toffee_unit = _unit(client, "Toffee", f"tf-{uuid.uuid4().hex[:6]}", "count")
    box = _product(
        client,
        box_unit["id"],
        "Toffee box",
        f"TOF-{uuid.uuid4().hex[:6]}",
        net_quantity="20",
        net_quantity_unit_id=toffee_unit["id"],
        selling_price="80",
        quantity_unit_price="5",
    )
    packed = _order(
        client,
        box["id"],
        box_unit["id"],
        items=[
            {
                "product_id": box["id"],
                "unit_id": box_unit["id"],
                "quantity": "1",
                "unit_price": "80",
                "discount_type": "AMOUNT",
                "discount_value": "0",
            }
        ],
    )
    assert packed.status_code == 201, packed.text
    assert packed.json()["items"][0]["subtotal"] == "80.00"


def test_complete_is_terminal_for_stock(client):
    bag = _unit(client, "Bag", f"bag-{uuid.uuid4().hex[:6]}", "packaging")
    product = _product(client, bag["id"], "Crush", f"CR-{uuid.uuid4().hex[:6]}")
    _stock(client, product["id"], bag["id"], "5", "20")
    created = _order(client, product["id"], bag["id"])
    order_id = created.json()["id"]
    assert client.post(f"/api/v1/orders/{order_id}/complete").status_code == 409
    client.post(f"/api/v1/orders/{order_id}/confirm")
    completed = client.post(f"/api/v1/orders/{order_id}/complete")
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "COMPLETED"
    assert client.post(f"/api/v1/orders/{order_id}/cancel").status_code == 409
    assert client.delete(f"/api/v1/orders/{order_id}").status_code == 409
    assert client.get(f"/api/v1/inventory/{product['id']}").json()["quantity_on_hand"] == "3.0000"
