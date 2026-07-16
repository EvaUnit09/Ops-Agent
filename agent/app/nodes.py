"""Factory functions that build the three async graph node callables.

Single responsibility: build_model_node() wraps a tools-bound model and
prepends SYSTEM_PROMPT; build_counted_tool_node() wraps LangGraph's ToolNode
and increments tool_rounds by one after every batch of parallel tool calls
(one assistant message = one round, not one per call), setting
soft_limit_reached when the count reaches max_tool_rounds;
build_finalizer_node() invokes the unbound base model with FINALIZER_PROMPT
so it produces a prose answer from evidence already in the message history
without requesting more tool calls.

_safe_tool_error() turns any exception raised inside a tool call into the
canonical {"error": {"kind", "message"}} JSON payload doc 00 defines for
ToolMessage content — branching on DomainApiError for its real kind/message,
on pydantic ValidationError for bad tool arguments, and falling back to a
generic unexpected_response for anything else. It never leaks raw exception
text from an unclassified failure.

Governed by:
  §"Graph loop and termination contract — Routing rules 3-6"
    in 00-roadmap-and-contracts.md
  §"Six canonical tool contracts" in 00-roadmap-and-contracts.md
  §"agent/app/nodes.py" in 02-langgraph-agent.md
"""

import json
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from langchain_core.messages import SystemMessage
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.prebuilt import ToolNode
from pydantic import ValidationError

from app.api_client import DomainApiError
from app.prompts import FINALIZER_PROMPT, SYSTEM_PROMPT
from app.state import AgentState

Node = Callable[[AgentState, RunnableConfig], Awaitable[dict[str, Any]]]


def build_model_node(model_with_tools: Runnable[Any, Any]) -> Node:
    async def call_model(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
        response = await model_with_tools.ainvoke(
            [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]], config=config
        )
        return {"messages": [response]}

    return call_model


def _safe_tool_error(exc: Exception) -> str:
    if isinstance(exc, DomainApiError):
        kind, message = exc.kind, exc.message
    elif isinstance(exc, ValidationError):
        kind, message = "invalid_request", "invalid tool arguments"
    else:
        kind, message = "unexpected_response", "tool lookup failed"
    return json.dumps({"error": {"kind": kind, "message": message}})


def build_counted_tool_node(tools: Sequence[BaseTool], *, max_tool_rounds: int) -> Node:
    tool_node = ToolNode(tools, handle_tool_errors=_safe_tool_error)

    async def call_tools(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
        result = await tool_node.ainvoke(state, config=config)
        next_round = state.get("tool_rounds", 0) + 1
        return {
            "messages": result["messages"],
            "tool_rounds": next_round,
            "soft_limit_reached": next_round >= max_tool_rounds,
        }

    return call_tools


def build_finalizer_node(finalizer_model: Runnable[Any, Any]) -> Node:
    async def finalize(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
        response = await finalizer_model.ainvoke(
            [SystemMessage(content=FINALIZER_PROMPT), *state["messages"]], config=config
        )
        return {"messages": [response], "soft_limit_reached": True}

    return finalize
