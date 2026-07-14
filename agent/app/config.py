"""Validated application settings loaded from environment variables.

Single responsibility: read every env var the agent needs (API key, model,
domain API URL, checkpoint URL/schema, timeout/retry tuning, tool-round cap,
recursion limit, log level) and expose them through a cached Settings object.

Governed by:
  §"Environment-variable matrix / Agent and checkpointer" in 00-roadmap-and-contracts.md
  §"agent/app/config.py" in 02-langgraph-agent.md
"""
