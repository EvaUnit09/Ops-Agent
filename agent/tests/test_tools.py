import json

import pytest
from pydantic import ValidationError

from app.tools import build_tools
from tests.conftest import FakeDomainClient


def tools(client: FakeDomainClient) -> dict[str, object]:
    return {item.name: item for item in build_tools(client)}


async def test_names_paths_and_normalized_result() -> None:
    client = FakeDomainClient({"/assets/search": [{"id": 1}]})
    items = tools(client)
    assert set(items) == {
        "search_assets",
        "find_stale_assets",
        "get_assets_by_department",
        "get_checkout_history",
        "get_user_assets",
        "search_users_by_department",
    }
    result = await items["search_assets"].ainvoke(
        {"category": "laptop", "status": "available", "limit": 10}
    )
    await items["find_stale_assets"].ainvoke(
        {
            "stale_days": 31,
            "category": "monitor",
            "status": "checked_out",
            "region": "emea",
        }
    )
    await items["get_assets_by_department"].ainvoke(
        {
            "department": "Engineering",
            "category": "laptop",
            "status": "available",
            "region": "us-east",
            "stale_days": 90,
        }
    )
    await items["get_checkout_history"].ainvoke({"asset_id": 42})
    await items["get_user_assets"].ainvoke({"user_id": 9})
    await items["search_users_by_department"].ainvoke(
        {"department": "Engineering", "query": "ada"}
    )
    assert json.loads(result) == {"count": 1, "items": [{"id": 1}]}
    assert client.calls == [
        (
            "/assets/search",
            {"category": "laptop", "status": "available", "region": None, "limit": 10},
        ),
        (
            "/assets/stale",
            {
                "stale_days": 31,
                "category": "monitor",
                "status": "checked_out",
                "region": "emea",
            },
        ),
        (
            "/assets/by-department",
            {
                "department": "Engineering",
                "category": "laptop",
                "status": "available",
                "region": "us-east",
                "stale_days": 90,
            },
        ),
        ("/checkouts/asset/42", {}),
        ("/checkouts/user/9", {}),
        ("/users/search", {"department": "Engineering", "q": "ada"}),
    ]


async def test_search_assets_sends_null_limit_when_not_supplied() -> None:
    # The tool always includes a `limit` key; DomainApiClient (not the tool
    # or this fake) is what strips None-valued params before the HTTP call.
    client = FakeDomainClient({"/assets/search": []})
    items = tools(client)
    await items["search_assets"].ainvoke({"category": "laptop"})
    assert client.calls == [
        ("/assets/search", {"category": "laptop", "status": None, "region": None, "limit": None})
    ]


def test_closed_department_schema_rejects_unknown_value() -> None:
    item = tools(FakeDomainClient())["search_users_by_department"]
    with pytest.raises(ValidationError):
        item.args_schema.model_validate({"department": "Legal"})


@pytest.mark.parametrize("stale_days", [0, 3651])
def test_stale_day_ranges_reject_out_of_bounds(stale_days: int) -> None:
    items = tools(FakeDomainClient())
    with pytest.raises(ValidationError):
        items["find_stale_assets"].args_schema.model_validate({"stale_days": stale_days})
    with pytest.raises(ValidationError):
        items["get_assets_by_department"].args_schema.model_validate(
            {"department": "Engineering", "stale_days": stale_days}
        )


@pytest.mark.parametrize("limit", [0, 101])
def test_search_assets_limit_rejects_out_of_bounds(limit: int) -> None:
    item = tools(FakeDomainClient())["search_assets"]
    with pytest.raises(ValidationError):
        item.args_schema.model_validate({"limit": limit})
