def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    api_response = client.get("/api/v1/health")
    assert api_response.status_code == 200
