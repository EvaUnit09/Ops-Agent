from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import services
from app.models import Asset, AssetCategory, AssetStatus, Region


def test_asset_search_applies_enum_filters(
    client: TestClient,
    sample_data: dict[str, int],
) -> None:
    response = client.get(
        "/assets/search",
        params={
            "category": "monitor",
            "status": "available",
            "region": "emea",
            "limit": 2,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["tag"] for item in body["data"]] == ["AST-000001"]
    assert body["data"][0]["current_holder"] is None
    assert body["meta"] == {"count": 1, "limit": 2}


def test_stale_service_includes_asset_exactly_at_cutoff(
    db: Session,
) -> None:
    cutoff = datetime(2026, 1, 1, tzinfo=UTC)
    asset = Asset(
        tag="AST-CUTOFF",
        category=AssetCategory.tablet,
        model="Surface Pro 11",
        status=AssetStatus.available,
        region=Region.apac,
        last_synced_at=cutoff,
    )
    db.add(asset)
    db.commit()

    items = services.stale_assets(
        db,
        cutoff=cutoff,
        category=AssetCategory.tablet,
        status=AssetStatus.available,
        region=Region.apac,
        limit=50,
    )

    assert [item.id for item in items] == [asset.id]


def test_stale_assets_apply_enum_filters(
    client: TestClient,
    sample_data: dict[str, int],
) -> None:
    response = client.get(
        "/assets/stale",
        params={
            "stale_days": 30,
            "category": "laptop",
            "status": "checked_out",
            "region": "us-east",
        },
    )

    assert response.status_code == 200
    assert [item["tag"] for item in response.json()["data"]] == ["AST-000002"]


def test_assets_by_department_uses_open_checkout(
    client: TestClient,
    sample_data: dict[str, int],
) -> None:
    response = client.get(
        "/assets/by-department",
        params={
            "department": "Engineering",
            "category": "laptop",
            "status": "checked_out",
            "region": "us-east",
            "stale_days": 30,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["tag"] for item in body["data"]] == ["AST-000002"]
    assert body["data"][0]["current_holder"]["department"] == "Engineering"


def test_asset_detail_and_not_found_share_envelope(
    client: TestClient,
    sample_data: dict[str, int],
) -> None:
    found = client.get(f"/assets/{sample_data['checked_out_asset_id']}")
    missing = client.get("/assets/999999")

    assert found.status_code == 200
    assert found.json()["meta"] == {"count": 1, "limit": None}
    assert missing.status_code == 404
    assert missing.json() == {
        "data": None,
        "error": {
            "code": "http_404",
            "message": "asset not found",
        },
        "meta": {"count": 0, "limit": None},
    }
