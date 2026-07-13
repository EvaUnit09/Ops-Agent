from fastapi.testclient import TestClient


def test_user_search_requires_department_but_not_q(
    client: TestClient,
    sample_data: dict[str, int],
) -> None:
    response = client.get(
        "/users/search",
        params={"department": "Engineering"},
    )

    assert response.status_code == 200
    assert [user["email"] for user in response.json()["data"]] == ["ada@example.com"]


def test_user_search_applies_optional_literal_q(
    client: TestClient,
    sample_data: dict[str, int],
) -> None:
    match = client.get(
        "/users/search",
        params={"department": "Marketing", "q": "morgan"},
    )
    literal_percent = client.get(
        "/users/search",
        params={"department": "Marketing", "q": "%"},
    )

    assert match.status_code == 200
    assert [user["email"] for user in match.json()["data"]] == ["morgan@example.com"]
    assert literal_percent.status_code == 200
    assert literal_percent.json()["data"] == []


def test_user_search_missing_department_uses_error_envelope(
    client: TestClient,
) -> None:
    response = client.get("/users/search")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
