import uuid
from datetime import date
from decimal import Decimal

from app.services.unit_conversion import sync_unit_conversions


def _unit(client, name, symbol, unit_type):
    response = client.post(
        "/api/v1/units",
        json={"name": name, "symbol": symbol, "unit_type": unit_type},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _product(client, unit_id, name, sku, **extra):
    category = client.post("/api/v1/categories", json={"name": f"Cat {sku}"}).json()
    payload = {
        "category_id": category["id"],
        "name": name,
        "sku": sku,
        "selling_unit_id": unit_id,
        "cost_price": "900",
        "selling_price": "1100",
        "status": "active",
        "attribute_values": [],
    }
    payload.update(extra)
    response = client.post("/api/v1/products", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _move(client, path, product_id, unit_id, quantity, unit_cost=None, post=True, **extra):
    item = {"product_id": product_id, "unit_id": unit_id, "quantity": str(quantity)}
    if unit_cost is not None:
        item["unit_cost"] = str(unit_cost)
    payload = {
        "transaction_date": "2026-11-18",
        "post": post,
        "items": [item],
    }
    payload.update(extra)
    response = client.post(path, json=payload)
    return response


def test_inventory_is_open_without_credentials(client):
    response = client.get("/api/v1/inventory")
    assert response.status_code == 200
    assert response.json()["items"] == []
    summary = client.get("/api/v1/inventory/summary")
    assert summary.status_code == 200
    assert summary.json()["product_count"] == 0


def test_opening_receipt_issue_and_weighted_average(client):
    bag = _unit(client, "Bag", "bag", "packaging")
    product = _product(client, bag["id"], "Maple Leaf 50kg", "CEM-50")
    opening = _move(client, "/api/v1/inventory/opening-stock", product["id"], bag["id"], "100", "1000")
    assert opening.status_code == 201, opening.text
    body = opening.json()
    assert body["status"] == "POSTED"
    assert body["transaction_number"].startswith("INV-2026-")
    assert body["total_value"] == "100000.00"

    receipt = _move(client, "/api/v1/inventory/receipts", product["id"], bag["id"], "50", "1200")
    assert receipt.status_code == 201, receipt.text
    detail = client.get(f"/api/v1/inventory/{product['id']}")
    assert detail.status_code == 200
    stock = detail.json()
    assert Decimal(stock["quantity_on_hand"]) == Decimal("150")
    assert Decimal(stock["average_cost"]) == Decimal("1066.666667")
    assert Decimal(stock["inventory_value"]) == Decimal("160000.00")

    issue = _move(
        client,
        "/api/v1/inventory/issues",
        product["id"],
        bag["id"],
        "20",
        reason="Internal usage",
    )
    assert issue.status_code == 201, issue.text
    assert Decimal(issue.json()["items"][0]["total_cost"]) == Decimal("21333.33")
    after = client.get(f"/api/v1/inventory/{product['id']}").json()
    assert Decimal(after["quantity_on_hand"]) == Decimal("130")
    assert Decimal(after["inventory_value"]) == Decimal("138666.67")
    assert Decimal(after["average_cost"]) == Decimal("1066.666667")


def test_issue_path_is_under_inventory(client):
    bag = _unit(client, "Bag", "bag2", "packaging")
    product = _product(client, bag["id"], "Sand", "SAND-1")
    _move(client, "/api/v1/inventory/opening-stock", product["id"], bag["id"], "10", "5")
    issue = _move(client, "/api/v1/inventory/issues", product["id"], bag["id"], "4", reason="Damaged")
    assert issue.status_code == 201, issue.text
    assert issue.json()["transaction_type"] == "STOCK_ISSUE"
    assert Decimal(issue.json()["items"][0]["total_cost"]) == Decimal("20.00")


def test_adjustment_increase_and_decrease(client):
    piece = _unit(client, "Piece", "pc", "count")
    product = _product(client, piece["id"], "Steel rod", "ROD-12")
    _move(client, "/api/v1/inventory/opening-stock", product["id"], piece["id"], "100", "250")
    increase = client.post(
        "/api/v1/inventory/adjustments",
        json={
            "transaction_date": "2026-11-18",
            "reason": "Physical count",
            "post": True,
            "items": [{"product_id": product["id"], "unit_id": piece["id"], "physical_quantity": "105"}],
        },
    )
    assert increase.status_code == 201, increase.text
    assert Decimal(increase.json()["items"][0]["quantity_delta"]) == Decimal("5")
    decrease = client.post(
        "/api/v1/inventory/adjustments",
        json={
            "transaction_date": "2026-11-18",
            "reason": "Physical count",
            "post": True,
            "items": [{"product_id": product["id"], "unit_id": piece["id"], "physical_quantity": "95"}],
        },
    )
    assert decrease.status_code == 201, decrease.text
    assert Decimal(decrease.json()["items"][0]["quantity_delta"]) == Decimal("-10")
    stock = client.get(f"/api/v1/inventory/{product['id']}").json()
    assert Decimal(stock["quantity_on_hand"]) == Decimal("95")
    assert Decimal(stock["inventory_value"]) == Decimal("23750.00")


def test_bag_and_weight_conversion(client, db):
    bag = _unit(client, "Bag", "bag3", "packaging")
    kg = _unit(client, "Kilogram", "kg", "weight")
    ton = _unit(client, "Ton", "ton", "weight")
    sync_unit_conversions(db)
    product = _product(
        client,
        bag["id"],
        "Cement bag",
        "CEM-BAG",
        net_quantity="50",
        net_quantity_unit_id=kg["id"],
    )
    received = client.post(
        "/api/v1/inventory/receipts",
        json={
            "transaction_date": "2026-11-18",
            "post": True,
            "items": [
                {
                    "product_id": product["id"],
                    "unit_id": ton["id"],
                    "quantity": "0.5",
                    "unit_cost": "24000",
                }
            ],
        },
    )
    assert received.status_code == 201, received.text
    stock = client.get(f"/api/v1/inventory/{product['id']}").json()
    assert Decimal(stock["quantity_on_hand"]) == Decimal("10")
    assert Decimal(stock["inventory_value"]) == Decimal("12000.00")
    assert Decimal(stock["average_cost"]) == Decimal("1200.000000")


def test_rejects_invalid_lines(client):
    bag = _unit(client, "Bag", "bag4", "packaging")
    other = _unit(client, "Meter", "m", "length")
    product = _product(client, bag["id"], "Blocks", "BLK-1")
    missing = _move(client, "/api/v1/inventory/receipts", str(uuid.uuid4()), bag["id"], "1", "10")
    assert missing.status_code == 404
    inactive = client.post(
        "/api/v1/products",
        json={
            "category_id": product["category_id"],
            "name": "Draft blocks",
            "sku": "BLK-D",
            "selling_unit_id": bag["id"],
            "cost_price": "1",
            "selling_price": "2",
            "status": "draft",
            "attribute_values": [],
        },
    ).json()
    draft_move = _move(client, "/api/v1/inventory/receipts", inactive["id"], bag["id"], "1", "10")
    assert draft_move.status_code == 422
    bad_unit = _move(client, "/api/v1/inventory/receipts", product["id"], other["id"], "1", "10")
    assert bad_unit.status_code == 422
    assert "not compatible" in bad_unit.json()["detail"]
    zero = _move(client, "/api/v1/inventory/receipts", product["id"], bag["id"], "0", "10")
    assert zero.status_code == 422
    negative = _move(client, "/api/v1/inventory/receipts", product["id"], bag["id"], "-2", "10")
    assert negative.status_code == 422
    unknown_unit = _move(client, "/api/v1/inventory/receipts", product["id"], str(uuid.uuid4()), "1", "10")
    assert unknown_unit.status_code == 422


def test_insufficient_stock_duplicate_post_and_reversal(client):
    bag = _unit(client, "Bag", "bag5", "packaging")
    product = _product(client, bag["id"], "Paint", "PNT-1")
    opening = _move(client, "/api/v1/inventory/opening-stock", product["id"], bag["id"], "10", "15")
    assert opening.status_code == 201, opening.text
    again = _move(client, "/api/v1/inventory/opening-stock", product["id"], bag["id"], "1", "15")
    assert again.status_code == 422
    short = _move(client, "/api/v1/inventory/issues", product["id"], bag["id"], "11", reason="Internal usage")
    assert short.status_code == 422
    assert "Insufficient stock" in short.json()["detail"]
    draft = _move(
        client,
        "/api/v1/inventory/issues",
        product["id"],
        bag["id"],
        "2",
        post=False,
        reason="Internal usage",
    )
    assert draft.status_code == 201
    transaction_id = draft.json()["id"]
    posted = client.post(f"/api/v1/inventory/transactions/{transaction_id}/post")
    assert posted.status_code == 200, posted.text
    duplicate = client.post(f"/api/v1/inventory/transactions/{transaction_id}/post")
    assert duplicate.status_code == 409
    reversal = client.post(f"/api/v1/inventory/transactions/{opening.json()['id']}/reverse")
    assert reversal.status_code == 422
    issued = client.post(f"/api/v1/inventory/transactions/{transaction_id}/reverse")
    assert issued.status_code == 201, issued.text
    assert issued.json()["transaction_type"] == "REVERSAL"
    second = client.post(f"/api/v1/inventory/transactions/{transaction_id}/reverse")
    assert second.status_code == 409
    stock = client.get(f"/api/v1/inventory/{product['id']}").json()
    assert Decimal(stock["quantity_on_hand"]) == Decimal("10")


def test_invalid_second_line_does_not_change_stock(client):
    bag = _unit(client, "Bag", "bag6", "packaging")
    product = _product(client, bag["id"], "Nails", "NAIL-1")
    response = client.post(
        "/api/v1/inventory/receipts",
        json={
            "transaction_date": "2026-11-18",
            "post": True,
            "items": [
                {"product_id": product["id"], "unit_id": bag["id"], "quantity": "4", "unit_cost": "3"},
                {"product_id": str(uuid.uuid4()), "unit_id": bag["id"], "quantity": "1", "unit_cost": "3"},
            ],
        },
    )
    assert response.status_code == 404
    stock = client.get(f"/api/v1/inventory/{product['id']}").json()
    assert Decimal(stock["quantity_on_hand"]) == Decimal("0")


def test_duplicate_product_negative_cost_and_guards(client):
    bag = _unit(client, "Bag", "bag7", "packaging")
    other = _unit(client, "Piece", "pc2", "count")
    product = _product(client, bag["id"], "Wire", "WIRE-1")
    duplicate = client.post(
        "/api/v1/inventory/receipts",
        json={
            "transaction_date": "2026-11-18",
            "post": True,
            "items": [
                {"product_id": product["id"], "unit_id": bag["id"], "quantity": "1", "unit_cost": "5"},
                {"product_id": product["id"], "unit_id": bag["id"], "quantity": "1", "unit_cost": "5"},
            ],
        },
    )
    assert duplicate.status_code == 422
    assert "Duplicate product" in duplicate.json()["detail"]
    _move(client, "/api/v1/inventory/opening-stock", product["id"], bag["id"], "6", "8")
    changed = client.patch(
        f"/api/v1/products/{product['id']}",
        json={
            "category_id": product["category_id"],
            "name": product["name"],
            "sku": product["sku"],
            "selling_unit_id": other["id"],
            "cost_price": product["cost_price"],
            "selling_price": product["selling_price"],
            "status": "active",
            "attribute_values": [],
        },
    )
    assert changed.status_code == 409
    removed = client.delete(f"/api/v1/products/{product['id']}")
    assert removed.status_code == 409


def test_low_stock_history_and_reports(client):
    bag = _unit(client, "Bag", "bag8", "packaging")
    product = _product(client, bag["id"], "Lime", "LIME-1")
    _move(client, "/api/v1/inventory/opening-stock", product["id"], bag["id"], "4", "20")
    settings = client.put(
        f"/api/v1/inventory/{product['id']}/settings",
        json={"minimum_stock_level": "10", "reorder_level": "8", "maximum_stock_level": "40"},
    )
    assert settings.status_code == 200, settings.text
    listed = client.get("/api/v1/inventory", params={"status": "low_stock", "q": "LIME"})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["stock_status"] == "low_stock"
    history = client.get(f"/api/v1/inventory/{product['id']}/history")
    assert history.status_code == 200
    assert history.json()[0]["transaction_type"] == "OPENING_STOCK"
    report = client.get("/api/v1/inventory/reports/low-stock")
    assert report.status_code == 200
    assert any(row[1] == "LIME-1" for row in report.json()["rows"])
    exported = client.get("/api/v1/inventory/reports/valuation", params={"format": "csv"})
    assert exported.status_code == 200
    assert "text/csv" in exported.headers["content-type"]
    assert "LIME-1" in exported.text
    summary = client.get("/api/v1/inventory/summary")
    assert summary.status_code == 200
    assert summary.json()["low_stock_count"] == 1
    _move(client, "/api/v1/inventory/issues", product["id"], bag["id"], "4", reason="Internal usage")
    out = client.get("/api/v1/inventory/reports/out-of-stock")
    assert any(row[1] == "LIME-1" for row in out.json()["rows"])
    movements = client.get(
        "/api/v1/inventory/reports/movements",
        params={"date_from": "2026-11-01", "date_to": "2026-11-30", "q": "LIME-1"},
    )
    assert movements.status_code == 200
    assert len(movements.json()["rows"]) == 2


def test_draft_edit_and_delete(client):
    bag = _unit(client, "Bag", "bag9", "packaging")
    product = _product(client, bag["id"], "Putty", "PUTTY-1")
    draft = _move(client, "/api/v1/inventory/receipts", product["id"], bag["id"], "3", "12", post=False)
    assert draft.json()["status"] == "DRAFT"
    updated = client.put(
        f"/api/v1/inventory/transactions/{draft.json()['id']}",
        json={
            "transaction_date": "2026-11-18",
            "items": [{"product_id": product["id"], "unit_id": bag["id"], "quantity": "5", "unit_cost": "12"}],
        },
    )
    assert updated.status_code == 200, updated.text
    assert Decimal(updated.json()["items"][0]["quantity"]) == Decimal("5")
    deleted = client.delete(f"/api/v1/inventory/transactions/{draft.json()['id']}")
    assert deleted.status_code == 204
    missing = client.get(f"/api/v1/inventory/transactions/{draft.json()['id']}")
    assert missing.status_code == 404
    stock = client.get(f"/api/v1/inventory/{product['id']}").json()
    assert Decimal(stock["quantity_on_hand"]) == Decimal("0")
