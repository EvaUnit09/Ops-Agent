from fastapi.testclient import TestClient


def test_checkouts_for_asset_return_complete_history(
    client: TestClient,
    sample_data: dict[str, int],
) -> None:
    response = client.get(f"/checkouts/asset/{sample_data['checked_out_asset_id']}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 2
    assert data[0]["id"] == sample_data["open_checkout_id"]
    assert data[0]["checked_in_at"] is None
    assert data[0]["user"]["email"] == "ada@example.com"
    assert data[1]["user"]["email"] == "morgan@example.com"
    assert response.json()["meta"] == {"count": 2, "limit": None}


def test_known_asset_without_history_returns_empty(
    client: TestClient,
    sample_data: dict[str, int],
) -> None:
    response = client.get(f"/checkouts/asset/{sample_data['available_asset_id']}")

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_unknown_asset_history_returns_404(client: TestClient) -> None:
    response = client.get("/checkouts/asset/999999")

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "asset not found"


def test_checkouts_for_user_return_only_current_asset_reads(
    client: TestClient,
    sample_data: dict[str, int],
) -> None:
    response = client.get(f"/checkouts/user/{sample_data['engineer_id']}")

    assert response.status_code == 200
    body = response.json()
    assert [item["tag"] for item in body["data"]] == ["AST-000002"]
    assert body["data"][0]["current_holder"]["email"] == "ada@example.com"
    assert "asset" not in body["data"][0]
    assert body["meta"] == {"count": 1, "limit": None}


def test_user_with_only_past_checkout_has_no_current_assets(
    client: TestClient,
    sample_data: dict[str, int],
) -> None:
    response = client.get(f"/checkouts/user/{sample_data['marketer_id']}")

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_unknown_user_assets_returns_404(client: TestClient) -> None:
    response = client.get("/checkouts/user/999999")

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "user not found"
