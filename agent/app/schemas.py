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

from typing import Annotated
from pydantic import BaseModel, StringConstraints, ConfigDict, Field
import uuid
from langchain_core.messages import BaseMessage

class ChatRequest(BaseModel):
    message: Annotated[str, StringConstraints(max_length=4000, min_length=1, strip_whitespace=True)]
    thread_id: uuid.UUID
    model_config = ConfigDict(extra="forbid")

class ChatResponse(BaseModel):
    answer: Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
    thread_id: uuid.UUID
    tool_rounds: Annotated[int, Field(ge=0)]
    soft_limit_reached: bool

def message_text(message: BaseMessage) -> str:
    """Extract plain text from a message whose content may be a string or content blocks.

    Keeps bare strings and {"type": "text", "text": ...} dicts. Skips known
    non-text (tool_use, thinking, etc.) and unknown blocks silently.
    """
    if isinstance(message.content, str):
        return message.content
    parts: list[str] = []
    for block in message.content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "".join(parts)

