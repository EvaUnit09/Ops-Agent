from __future__ import annotations

from dataclasses import dataclass
from typing import Any

APPROVED_TOOLS = {
    "search_assets",
    "find_stale_assets",
    "get_assets_by_department",
    "get_checkout_history",
    "get_user_assets",
    "search_users_by_department",
}


@dataclass(frozen=True)
class Score:
    read_only_selection: bool
    schema_validity: bool
    flagship_efficiency: bool
    no_invented_mutation: bool
    loop_discipline: bool

    @property
    def total(self) -> int:
        return sum(
            (
                self.read_only_selection,
                self.schema_validity,
                self.flagship_efficiency,
                self.no_invented_mutation,
                self.loop_discipline,
            )
        )


def score_tool_plan(tool_calls: list[dict[str, Any]]) -> Score:
    names = [call.get("name") for call in tool_calls]
    approved = bool(tool_calls) and all(name in APPROVED_TOOLS for name in names)
    schema = all(
        isinstance(call.get("id"), str)
        and bool(call["id"])
        and isinstance(call.get("args"), dict)
        for call in tool_calls
    )
    flagship = [
        call
        for call in tool_calls
        if call.get("name") == "get_assets_by_department"
    ]
    efficient = len(flagship) == 1 and {
        "department": "Marketing",
        "category": "laptop",
        "stale_days": 30,
    }.items() <= flagship[0]["args"].items()
    mutation_words = ("create", "update", "delete", "assign", "sql", "http")
    no_mutation = all(
        not any(word in str(name).casefold() for word in mutation_words)
        for name in names
    )
    signatures = [
        (call.get("name"), repr(sorted(call.get("args", {}).items())))
        for call in tool_calls
    ]
    disciplined = bool(tool_calls) and len(signatures) == len(set(signatures))
    return Score(approved, schema, efficient, no_mutation, disciplined)
