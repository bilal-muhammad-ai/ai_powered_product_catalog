def test_category_tree_paths_and_delete_guard(client):
    parent = client.post("/api/v1/categories", json={"name": "Steel"}).json()
    child = client.post("/api/v1/categories", json={"name": "Rebar", "parent_id": parent["id"]}).json()
    assert child["path"] == "/steel/rebar/"

    blocked = client.delete(f"/api/v1/categories/{parent['id']}")
    assert blocked.status_code == 409

    moved = client.patch(f"/api/v1/categories/{child['id']}", json={"parent_id": None})
    assert moved.status_code == 200
    assert moved.json()["path"] == "/rebar/"

    cycle = client.patch(f"/api/v1/categories/{parent['id']}", json={"parent_id": parent["id"]})
    assert cycle.status_code == 422
