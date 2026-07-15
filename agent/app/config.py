"""Validated application settings loaded from environment variables.

Single responsibility: read every env var the agent needs (API key, model,
domain API URL, checkpoint URL/schema, timeout/retry tuning, tool-round cap,
recursion limit, log level) and expose them through a cached Settings object.

Governed by:
  §"Environment-variable matrix / Agent and checkpointer" in 00-roadmap-and-contracts.md
  §"agent/app/config.py" in 02-langgraph-agent.md
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).parent.parent / ".env")

    database_url: str = Field(..., env="DATABASE_URL")
    langchain_api_key: str = Field(..., env="LANGCHAIN_API_KEY")
    langchain_project: str = Field(..., env="LANGCHAIN_PROJECT")
    langchain_tracing_v2: bool = Field(..., env="LANGCHAIN_TRACING_V2")
    langchain_smith_endpoint: str = Field(..., env="LANGCHAIN_SMITH_ENDPOINT")
    langchain_smith_api_key: str = Field(..., env="LANGCHAIN_SMITH_API_KEY")

@lru_cache
def get_settings() -> Settings:
    return Settings()
