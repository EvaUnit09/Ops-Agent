from fastapi.testclient import TestClient


def test_health_uses_common_envelope(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "data": {"status": "ok", "database": "ok"},
        "error": None,
        "meta": {"count": 1, "limit": None},
    }
