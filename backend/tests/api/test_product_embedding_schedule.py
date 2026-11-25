import uuid


def _unit(client, symbol="bag"):
    response = client.post(
        "/api/v1/units",
        json={"name": symbol, "symbol": symbol, "unit_type": "packaging"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _cement(client):
    category = client.post("/api/v1/categories", json={"name": "Cement"}).json()
    type_attribute = client.post(
        f"/api/v1/categories/{category['id']}/attributes",
        json={"name": "Type", "code": "type", "data_type": "single_select", "is_required": True},
    ).json()
    opc = client.post(
        f"/api/v1/attributes/{type_attribute['id']}/options",
        json={"label": "OPC", "value": "opc"},
    ).json()
    weight = client.post(
        f"/api/v1/categories/{category['id']}/attributes",
        json={"name": "Bag weight", "code": "bag_weight", "data_type": "single_select", "is_required": True},
    ).json()
    bag50 = client.post(
        f"/api/v1/attributes/{weight['id']}/options",
        json={"label": "50 kg", "value": "50"},
    ).json()
    return category, type_attribute, opc, weight, bag50


def _body(category_id, unit_id, name, sku, type_id, type_option, weight_id, weight_option, price="1100"):
    return {
        "category_id": category_id,
        "name": name,
        "sku": sku,
        "selling_unit_id": unit_id,
        "cost_price": "900",
        "selling_price": price,
        "status": "active",
        "attribute_values": [
            {"attribute_id": type_id, "value": type_option},
            {"attribute_id": weight_id, "value": weight_option},
        ],
    }


def test_embedding_sync_follows_name_and_category_only(client, monkeypatch):
    recorded: list[uuid.UUID] = []

    def record(product_id: uuid.UUID) -> None:
        recorded.append(product_id)

    monkeypatch.setattr("app.api.v1.products.sync_product_embedding", record)

    unit = _unit(client)
    category, type_attribute, opc, weight, bag50 = _cement(client)
    child = client.post("/api/v1/categories", json={"name": "OPC bags", "parent_id": category["id"]})
    assert child.status_code == 201, child.text
    payload = _body(
        category["id"],
        unit["id"],
        "OPC Cement 50 kg",
        "CEM-50",
        type_attribute["id"],
        opc["id"],
        weight["id"],
        bag50["id"],
    )

    created = client.post("/api/v1/products", json=payload)
    assert created.status_code == 201, created.text
    product_id = uuid.UUID(created.json()["id"])
    assert recorded == [product_id]

    priced = client.patch(f"/api/v1/products/{product_id}", json=payload | {"selling_price": "1250.00"})
    assert priced.status_code == 200, priced.text
    assert priced.json()["selling_price"] == "1250.00"
    assert recorded == [product_id]

    renamed = client.patch(f"/api/v1/products/{product_id}", json=payload | {"name": "OPC Cement bag"})
    assert renamed.status_code == 200, renamed.text
    assert recorded == [product_id, product_id]

    moved = client.patch(
        f"/api/v1/products/{product_id}",
        json=payload | {"name": "OPC Cement bag", "category_id": child.json()["id"]},
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["category_id"] == child.json()["id"]
    assert recorded == [product_id, product_id, product_id]
