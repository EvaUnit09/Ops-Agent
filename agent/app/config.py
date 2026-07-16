"""Validated application settings loaded from environment variables.

Single responsibility: read every env var the agent needs (API key, model,
domain API URL, checkpoint URL/schema, timeout/retry tuning, tool-round cap,
recursion limit, CORS origins, log level) and expose them through a cached
Settings object.

Governed by:
  §"Environment-variable matrix / Agent and checkpointer" in 00-roadmap-and-contracts.md
  §"agent/app/config.py" in 02-langgraph-agent.md
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = Field(alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-sonnet-4-6", alias="ANTHROPIC_MODEL")
    api_base_url: str = Field(default="http://api:8000", alias="API_BASE_URL")
    checkpoint_database_url: str = Field(alias="CHECKPOINT_DATABASE_URL")
    checkpoint_schema: str = Field(default="agent_checkpoints", alias="CHECKPOINT_SCHEMA")
    api_timeout_seconds: float = Field(default=5.0, gt=0, alias="API_TIMEOUT_SECONDS")
    api_max_retries: int = Field(default=2, ge=0, alias="API_MAX_RETRIES")
    api_retry_delay_seconds: float = Field(default=0.1, ge=0, alias="API_RETRY_DELAY_SECONDS")
    max_tool_rounds: int = Field(default=4, ge=1, le=10, alias="MAX_TOOL_ROUNDS")
    recursion_limit: int = Field(default=25, ge=5, le=100, alias="RECURSION_LIMIT")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", alias="LOG_LEVEL"
    )

    @field_validator("api_base_url")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("checkpoint_schema")
    @classmethod
    def validate_schema(cls, value: str) -> str:
        if not value.isidentifier():
            raise ValueError("CHECKPOINT_SCHEMA must be a valid SQL identifier")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
