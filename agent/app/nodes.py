"""Factory functions that build the three async graph node callables.

Single responsibility: build_model_node() wraps a tools-bound model and
prepends SYSTEM_PROMPT; build_counted_tool_node() wraps LangGraph's ToolNode
and increments tool_rounds by one after every batch of parallel tool calls
(one assistant message = one round, not one per call), setting
soft_limit_reached when the count reaches max_tool_rounds;
build_finalizer_node() invokes the unbound base model with FINALIZER_PROMPT
so it produces a prose answer from evidence already in the message history
without requesting more tool calls.

Governed by:
  §"Graph loop and termination contract — Routing rules 3-6"
    in 00-roadmap-and-contracts.md
  §"agent/app/nodes.py" in 02-langgraph-agent.md
"""
