"""FastAPI application entry point with lifespan resource management.

Single responsibility: create_app() builds the FastAPI application; its
lifespan context manager initialises shared resources in order (create the
agent_checkpoints schema via a one-shot admin connection, open the async
connection pool with a per-connection search_path callback, call
AsyncPostgresSaver.setup(), compile the graph) and tears them down cleanly.
Exposes GET /health and POST /chat; the chat handler resets tool_rounds and
soft_limit_reached to zero/False on every request, invokes the graph under
the frontend-supplied thread_id in configurable, extracts the last non-tool
AIMessage, and returns the four-field ChatResponse. Handles
GraphRecursionError as 500 and a missing final answer as 502; never leaks
stack traces or upstream error details in responses.

Governed by:
  §"Exact chat contract" in 00-roadmap-and-contracts.md
  §"Architecture and data flow / Agent" in 00-roadmap-and-contracts.md
  §"agent/app/main.py" in 02-langgraph-agent.md
"""
