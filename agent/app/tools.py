"""Six read-only LangChain tools that wrap the domain API.

Single responsibility: define build_tools(client) which returns the exact six
tools — search_assets, find_stale_assets, get_assets_by_department,
get_checkout_history, get_user_assets, search_users_by_department — each with
strict Pydantic args schemas (extra='forbid', closed Literal enums, bounded
integer ranges) and mapping to the exact domain API paths and query parameter
names specified in the contract. Every tool normalises its result to the
deterministic {"count": N, "items": [...]} JSON string that ToolNode records
as the ToolMessage content. The search_users_by_department query argument maps
to the API's q parameter.

Governed by:
  §"Six canonical tool contracts" in 00-roadmap-and-contracts.md
  §"agent/app/tools.py" in 02-langgraph-agent.md
"""
