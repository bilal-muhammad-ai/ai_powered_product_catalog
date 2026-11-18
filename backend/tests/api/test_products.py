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
        json={
            "name": "Type",
            "code": "type",
            "data_type": "single_select",
            "is_required": True,
        },
    ).json()
    opc = client.post(
        f"/api/v1/attributes/{type_attribute['id']}/options",
        json={"label": "OPC", "value": "opc"},
    ).json()
    weight = client.post(
        f"/api/v1/categories/{category['id']}/attributes",
        json={
            "name": "Bag weight",
            "code": "bag_weight",
            "data_type": "single_select",
            "is_required": True,
        },
    ).json()
    bag20 = client.post(
        f"/api/v1/attributes/{weight['id']}/options",
        json={"label": "20 kg", "value": "20"},
    ).json()
    bag50 = client.post(
        f"/api/v1/attributes/{weight['id']}/options",
        json={"label": "50 kg", "value": "50"},
    ).json()
    return category, type_attribute, opc, weight, bag20, bag50


def _product(unit_id, name, sku, type_id, type_option, weight_id, weight_option, price="1100"):
    return {
        "category_id": None,
        "name": name,
        "sku": sku,
        "selling_unit_id": unit_id,
        "cost_price": "900",
        "selling_price": price,
        "attribute_values": [
            {"attribute_id": type_id, "value": type_option},
            {"attribute_id": weight_id, "value": weight_option},
        ],
    }


def test_attribute_rules(client):
    category = client.post("/api/v1/categories", json={"name": "Pipes"}).json()
    child = client.post("/api/v1/categories", json={"name": "PVC", "parent_id": category["id"]}).json()
    created = client.post(
        f"/api/v1/categories/{category['id']}/attributes",
        json={"name": "Material", "code": "material", "data_type": "text", "inherit_to_children": True},
    )
    assert created.status_code == 201
    duplicate = client.post(
        f"/api/v1/categories/{child['id']}/attributes",
        json={"name": "Material", "code": "material", "data_type": "text"},
    )
    assert duplicate.status_code == 409
    multi = client.post(
        f"/api/v1/categories/{category['id']}/attributes",
        json={"name": "Colours", "code": "colours", "data_type": "multi_select"},
    )
    assert multi.status_code == 201
    visible = client.get(f"/api/v1/categories/{child['id']}/attributes?include_inherited=true")
    assert any(item["code"] == "material" and item["inherited"] for item in visible.json())


def test_product_save_validates_schema_and_identity(client):
    unit = _unit(client)
    category, type_attribute, opc, weight, bag20, bag50 = _cement(client)

    def body(name, sku, type_option, weight_option, price="1100"):
        payload = _product(unit["id"], name, sku, type_attribute["id"], type_option, weight["id"], weight_option, price)
        payload["category_id"] = category["id"]
        payload["status"] = "active"
        return payload

    missing = client.post(
        "/api/v1/products",
        json=body("Incomplete", "CEM-1", opc["id"], bag50["id"]) | {"attribute_values": []},
    )
    assert missing.status_code == 422
    assert client.get("/api/v1/products").json()["total"] == 0

    bad_option = client.post(
        "/api/v1/products",
        json=body("Bad option", "CEM-2", bag50["id"], bag50["id"]),
    )
    assert bad_option.status_code == 422

    created = client.post("/api/v1/products", json=body("OPC Cement 50 kg", "CEM-50", opc["id"], bag50["id"]))
    assert created.status_code == 201, created.text
    saved = created.json()
    assert saved["sku"] == "CEM-50"
    assert saved["selling_price"] == "1100.00"
    assert any(item["code"] == "bag_weight" for item in saved["attribute_values"])

    duplicate_sku = client.post("/api/v1/products", json=body("OPC Cement copy", "CEM-50", opc["id"], bag20["id"]))
    assert duplicate_sku.status_code == 409

    other = client.post("/api/v1/products", json=body("OPC Cement 20 kg", "CEM-20", opc["id"], bag20["id"], "640"))
    assert other.status_code == 201, other.text

    filtered = client.get("/api/v1/products", params={"attr": "bag_weight:50"})
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["selling_price"] == "1100.00"

    updated = body("OPC Cement 50 kg", "CEM-50", opc["id"], bag50["id"], "1250.00")
    patched = client.patch(f"/api/v1/products/{saved['id']}", json=updated)
    assert patched.status_code == 200, patched.text
    assert patched.json()["selling_price"] == "1250.00"

    blocked_delete = client.delete(f"/api/v1/attributes/{weight['id']}")
    assert blocked_delete.status_code == 409
    deactivated = client.patch(f"/api/v1/attributes/{weight['id']}", json={"is_active": False})
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    category_blocked = client.delete(f"/api/v1/categories/{category['id']}")
    assert category_blocked.status_code == 409
