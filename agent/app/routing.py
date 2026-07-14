"""Conditional edge functions that control graph flow after each node.

Single responsibility: route_after_model() inspects the last message —
returning "tools" if it is an AIMessage with tool_calls, END otherwise;
route_after_tools() inspects soft_limit_reached — returning "finalize" if
True, "model" otherwise. Routing to "finalize" only after tools have
completed ensures every tool_call_id has a matching ToolMessage before the
finalizer receives the state, satisfying Anthropic's requirement that all
tool_use blocks have corresponding tool_result blocks.

Governed by:
  §"Graph loop and termination contract — Routing rules 1-2, 5-6"
    in 00-roadmap-and-contracts.md
  §"agent/app/routing.py" in 02-langgraph-agent.md
"""
