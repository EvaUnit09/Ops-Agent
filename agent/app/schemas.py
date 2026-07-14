"""Pydantic models for the POST /chat request and response envelopes.

Single responsibility: validate that incoming requests carry a non-empty
message (<=4 000 chars, whitespace-stripped) and a well-formed UUID thread_id,
and that outgoing responses contain exactly {answer, thread_id, tool_rounds,
soft_limit_reached}. Also provides message_text() to extract plain text from
an AIMessage whose content may be a string or a list of content blocks.

Governed by:
  §"Exact chat contract" in 00-roadmap-and-contracts.md
  §"agent/app/schemas.py" in 02-langgraph-agent.md
"""
