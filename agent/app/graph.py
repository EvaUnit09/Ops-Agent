"""Assembles nodes, edges, and checkpointer into the compiled StateGraph.

Single responsibility: build_graph() constructs the StateGraph[AgentState],
registers model / tools / finalize nodes using factories from nodes.py,
wires edges START->model, model->{tools|END}, tools->{model|finalize},
finalize->END using routing functions from routing.py, and compiles with
the injected checkpointer. Accepts an optional model argument so tests can
substitute a scripted fake without an Anthropic key. Only the model node
receives a tools-bound model; the finalizer node uses the unbound base model.

Governed by:
  §"Graph loop and termination contract" in 00-roadmap-and-contracts.md
  §"agent/app/graph.py" in 02-langgraph-agent.md
"""

from typing import Any

from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from app.api_client import DomainApiClient
from app.config import Settings
from app.nodes import build_counted_tool_node, build_finalizer_node, build_model_node
from app.routing import route_after_model, route_after_tools
from app.state import AgentState
from app.tools import build_tools


def build_graph(
    *,
    settings: Settings,
    client: DomainApiClient,
    checkpointer: BaseCheckpointSaver[Any],
    model: Any | None = None,
) -> Any:
    tools = build_tools(client)
    base_model = model or ChatAnthropic(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key,
        temperature=0,
        max_retries=1,
    )
    model_with_tools = base_model.bind_tools(tools)

    builder = StateGraph(AgentState)
    builder.add_node("model", build_model_node(model_with_tools))
    builder.add_node(
        "tools",
        build_counted_tool_node(tools, max_tool_rounds=settings.max_tool_rounds),
    )
    builder.add_node("finalize", build_finalizer_node(base_model))
    builder.add_edge(START, "model")
    builder.add_conditional_edges("model", route_after_model, {"tools": "tools", END: END})
    builder.add_conditional_edges(
        "tools", route_after_tools, {"model": "model", "finalize": "finalize"}
    )
    builder.add_edge("finalize", END)
    return builder.compile(checkpointer=checkpointer)
