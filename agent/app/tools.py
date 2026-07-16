"""Six read-only LangChain tools that wrap the domain API.

Single responsibility: define build_tools(client) which returns the exact six
tools — search_assets, find_stale_assets, get_assets_by_department,
get_checkout_history, get_user_assets, search_users_by_department — each with
strict Pydantic args schemas (extra='forbid', closed Literal enums, bounded
integer ranges) and mapping to the exact domain API paths and query parameter
names specified in the contract. Every tool normalises its result to the
deterministic {"count": N, "items": [...]} JSON string that ToolNode records
as the ToolMessage content. The search_users_by_department query argument maps
to the API's q parameter. A 404 (unknown asset/user) is never silently turned
into an empty result here — DomainApiClient raises DomainApiError instead, and
ToolNode's handle_tool_errors hook (see nodes.py) turns that into the
canonical {"error": {"kind", "message"}} ToolMessage payload.

Governed by:
  §"Six canonical tool contracts" in 00-roadmap-and-contracts.md
  §"agent/app/tools.py" in 02-langgraph-agent.md
"""

import json
from collections.abc import Sequence
from typing import Any, Literal

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, ConfigDict, Field

from app.api_client import DomainApiClient

type Category = Literal["laptop", "monitor", "phone", "desktop", "tablet"]
type Status = Literal["available", "checked_out", "retired"]
type Region = Literal["us-east", "us-west", "emea", "apac"]
type Department = Literal["Engineering", "Marketing", "Sales", "Finance", "IT", "HR", "Operations"]


class StrictArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SearchAssetsArgs(StrictArgs):
    category: Category | None = Field(default=None, description="Exact category.")
    status: Status | None = Field(default=None, description="Exact status.")
    region: Region | None = Field(default=None, description="Exact region.")
    limit: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="Maximum results to return; server defaults to 50 when omitted.",
    )


class FindStaleAssetsArgs(StrictArgs):
    stale_days: int = Field(ge=1, le=3650, description="Age threshold in whole days.")
    category: Category | None = Field(default=None, description="Optional exact category.")
    status: Status | None = Field(default=None, description="Optional exact status.")
    region: Region | None = Field(default=None, description="Optional exact region.")


class AssetsByDepartmentArgs(StrictArgs):
    department: Department
    category: Category | None = Field(default=None, description="Optional exact category.")
    status: Status | None = Field(default=None, description="Optional exact status.")
    region: Region | None = Field(default=None, description="Optional exact region.")
    stale_days: int | None = Field(
        default=None,
        ge=1,
        le=3650,
        description="Optional synchronization age threshold in whole days.",
    )


class SearchUsersArgs(StrictArgs):
    department: Department
    query: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Optional user name or email fragment.",
    )


class AssetIdArgs(StrictArgs):
    asset_id: int = Field(gt=0)


class UserIdArgs(StrictArgs):
    user_id: int = Field(gt=0)


def _items(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict) and isinstance(value.get("items"), list):
        return value["items"]
    if value in (None, {}):
        return []
    return [value]


def _result(value: Any) -> str:
    items = _items(value)
    return json.dumps({"count": len(items), "items": items}, sort_keys=True, default=str)


def build_tools(client: DomainApiClient) -> Sequence[BaseTool]:
    @tool(args_schema=SearchAssetsArgs)
    async def search_assets(
        category: Category | None = None,
        status: Status | None = None,
        region: Region | None = None,
        limit: int | None = None,
    ) -> str:
        """Search assets by optional exact category, status, region, and limit."""
        return _result(
            await client.get(
                "/assets/search",
                params={
                    "category": category,
                    "status": status,
                    "region": region,
                    "limit": limit,
                },
            )
        )

    @tool(args_schema=FindStaleAssetsArgs)
    async def find_stale_assets(
        stale_days: int,
        category: Category | None = None,
        status: Status | None = None,
        region: Region | None = None,
    ) -> str:
        """Find assets older than 1-3650 days with optional exact filters."""
        return _result(
            await client.get(
                "/assets/stale",
                params={
                    "stale_days": stale_days,
                    "category": category,
                    "status": status,
                    "region": region,
                },
            )
        )

    @tool(args_schema=AssetsByDepartmentArgs)
    async def get_assets_by_department(
        department: Department,
        category: Category | None = None,
        status: Status | None = None,
        region: Region | None = None,
        stale_days: int | None = None,
    ) -> str:
        """List department assets with optional exact and staleness filters."""
        return _result(
            await client.get(
                "/assets/by-department",
                params={
                    "department": department,
                    "category": category,
                    "status": status,
                    "region": region,
                    "stale_days": stale_days,
                },
            )
        )

    @tool(args_schema=AssetIdArgs)
    async def get_checkout_history(asset_id: int) -> str:
        """Get checkout history for one positive asset ID."""
        return _result(await client.get(f"/checkouts/asset/{asset_id}"))

    @tool(args_schema=UserIdArgs)
    async def get_user_assets(user_id: int) -> str:
        """List current assets for one positive user ID."""
        return _result(await client.get(f"/checkouts/user/{user_id}"))

    @tool(args_schema=SearchUsersArgs)
    async def search_users_by_department(
        department: Department,
        query: str | None = None,
    ) -> str:
        """Find department users, optionally matching a name or email fragment."""
        return _result(
            await client.get(
                "/users/search",
                params={"department": department, "q": query},
            )
        )

    return (
        search_assets,
        find_stale_assets,
        get_assets_by_department,
        get_checkout_history,
        get_user_assets,
        search_users_by_department,
    )
