"""LangGraph graph state definition.

Single responsibility: extend MessagesState with two request-local scalars —
tool_rounds (int, incremented once per model/tool cycle) and
soft_limit_reached (bool, set to True when tool_rounds reaches MAX_TOOL_ROUNDS).
The add_messages reducer on the inherited messages key preserves message and
tool-call IDs across checkpoint merges. Both scalars are reset to zero/False
at the start of every HTTP request; they are not restored from checkpoints.

Governed by:
  §"Graph loop and termination contract" in 00-roadmap-and-contracts.md
  §"agent/app/state.py" in 02-langgraph-agent.md
"""

from langgraph.graph import MessagesState


class AgentState(MessagesState):
    tool_rounds: int
    soft_limit_reached: bool
