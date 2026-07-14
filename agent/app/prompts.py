"""Static system prompt strings for the model node and finalizer node.

Single responsibility: define SYSTEM_PROMPT (injected before every model
invocation, instructs the assistant to use tools for domain facts and never
fabricate data) and FINALIZER_PROMPT (injected only in the no-tools finalizer
node when the soft tool-round cap is reached, instructs the assistant to
summarise gathered evidence and state what could not be resolved).

Governed by:
  §"Graph loop and termination contract — The dedicated finalizer is required"
    in 00-roadmap-and-contracts.md
  §"agent/app/prompts.py" in 02-langgraph-agent.md
"""
