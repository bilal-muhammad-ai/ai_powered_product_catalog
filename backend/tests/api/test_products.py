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
            "scope": "product",
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
            "scope": "variant",
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


def _variant(unit_id, sku, option_id, weight_id):
    return {
        "sku": sku,
        "selling_unit_id": unit_id,
        "cost_price": "900",
        "selling_price": "1100",
        "attribute_values": [{"attribute_id": weight_id, "value": option_id}],
    }


def test_attribute_rules(client):
    category = client.post("/api/v1/categories", json={"name": "Pipes"}).json()
    child = client.post("/api/v1/categories", json={"name": "PVC", "parent_id": category["id"]}).json()
    created = client.post(
        f"/api/v1/categories/{category['id']}/attributes",
        json={"name": "Material", "code": "material", "data_type": "text", "scope": "product", "inherit_to_children": True},
    )
    assert created.status_code == 201
    duplicate = client.post(
        f"/api/v1/categories/{child['id']}/attributes",
        json={"name": "Material", "code": "material", "data_type": "text", "scope": "product"},
    )
    assert duplicate.status_code == 409
    multi = client.post(
        f"/api/v1/categories/{category['id']}/attributes",
        json={"name": "Colours", "code": "colours", "data_type": "multi_select", "scope": "variant"},
    )
    assert multi.status_code == 422
    visible = client.get(f"/api/v1/categories/{child['id']}/attributes?include_inherited=true")
    assert any(item["code"] == "material" and item["inherited"] for item in visible.json())


def test_product_save_validates_schema_and_variant_identity(client):
    unit = _unit(client)
    category, type_attribute, opc, weight, bag20, bag50 = _cement(client)
    missing = client.post(
        "/api/v1/products",
        json={
            "category_id": category["id"],
            "name": "Incomplete",
            "attribute_values": [],
            "variants": [_variant(unit["id"], "CEM-1", bag50["id"], weight["id"])],
        },
    )
    assert missing.status_code == 422
    assert client.get("/api/v1/products").json()["total"] == 0

    bad_option = client.post(
        "/api/v1/products",
        json={
            "category_id": category["id"],
            "name": "Bad option",
            "attribute_values": [{"attribute_id": type_attribute["id"], "value": bag50["id"]}],
            "variants": [_variant(unit["id"], "CEM-2", bag50["id"], weight["id"])],
        },
    )
    assert bad_option.status_code == 422

    duplicate_axis = client.post(
        "/api/v1/products",
        json={
            "category_id": category["id"],
            "name": "Duplicate bags",
            "attribute_values": [{"attribute_id": type_attribute["id"], "value": opc["id"]}],
            "variants": [
                _variant(unit["id"], "CEM-50A", bag50["id"], weight["id"]),
                _variant(unit["id"], "CEM-50B", bag50["id"], weight["id"]),
            ],
        },
    )
    assert duplicate_axis.status_code == 422

    created = client.post(
        "/api/v1/products",
        json={
            "category_id": category["id"],
            "name": "OPC Cement",
            "status": "active",
            "attribute_values": [{"attribute_id": type_attribute["id"], "value": opc["id"]}],
            "variants": [
                _variant(unit["id"], "CEM-20", bag20["id"], weight["id"]),
                _variant(unit["id"], "CEM-50", bag50["id"], weight["id"]),
            ],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert len(body["variants"]) == 2
    assert body["variants"][0]["variant_key"] != body["variants"][1]["variant_key"]

    filtered = client.get("/api/v1/products", params={"attr": "bag_weight:50"})
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1

    variant_id = body["variants"][1]["id"]
    patched = client.patch(f"/api/v1/variants/{variant_id}", json={"selling_price": "1250.00"})
    assert patched.status_code == 200
    assert patched.json()["selling_price"] == "1250.00"

    blocked_delete = client.delete(f"/api/v1/attributes/{weight['id']}")
    assert blocked_delete.status_code == 409
    deactivated = client.patch(f"/api/v1/attributes/{weight['id']}", json={"is_active": False})
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    category_blocked = client.delete(f"/api/v1/categories/{category['id']}")
    assert category_blocked.status_code == 409
