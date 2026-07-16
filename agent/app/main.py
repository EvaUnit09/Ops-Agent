"""FastAPI application entry point with lifespan resource management.

Single responsibility: create_app() builds the FastAPI application; its
lifespan context manager initialises shared resources in order (create the
agent_checkpoints schema via a one-shot admin connection, open the async
connection pool with a per-connection search_path callback, call
AsyncPostgresSaver.setup(), compile the graph) and tears them down cleanly.
Exposes GET /health and POST /chat; the chat handler resets tool_rounds and
soft_limit_reached to zero/False on every request, invokes the graph under
the frontend-supplied thread_id in configurable, extracts the last non-tool
AIMessage, and returns the four-field ChatResponse. Both a LangGraph
recursion-limit failure and a missing final answer are unexpected graph
outcomes, so both return 503; never leaks stack traces or upstream error
details in responses. CORS origins come from Settings.cors_origins, not a
hardcoded list.

Governed by:
  §"Exact chat contract" in 00-roadmap-and-contracts.md
  §"Architecture and data flow / Agent" in 00-roadmap-and-contracts.md
  §"agent/app/main.py" in 02-langgraph-agent.md
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.errors import GraphRecursionError
from psycopg import AsyncConnection, sql
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.api_client import DomainApiClient
from app.config import Settings, get_settings
from app.graph import build_graph
from app.schemas import ChatRequest, ChatResponse, message_text

logger = logging.getLogger(__name__)


async def _ensure_checkpoint_schema(database_url: str, schema: str) -> None:
    connection = await AsyncConnection.connect(database_url, autocommit=True)
    try:
        statement = sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema))
        await connection.execute(statement)
    finally:
        await connection.close()


def _connection_configurer(schema: str) -> Any:
    async def configure(connection: AsyncConnection[Any]) -> None:
        statement = sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema))
        await connection.execute(statement)

    return configure


def create_app(settings: Settings | None = None) -> FastAPI:
    active = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logging.basicConfig(level=active.log_level)
        http_client = httpx.AsyncClient(
            base_url=active.api_base_url,
            timeout=httpx.Timeout(active.api_timeout_seconds),
        )
        client = DomainApiClient(
            http_client,
            max_retries=active.api_max_retries,
            retry_delay_seconds=active.api_retry_delay_seconds,
        )
        pool = AsyncConnectionPool(
            conninfo=active.checkpoint_database_url,
            min_size=1,
            max_size=5,
            open=False,
            kwargs={"autocommit": True, "row_factory": dict_row},
            configure=_connection_configurer(active.checkpoint_schema),
        )
        try:
            await _ensure_checkpoint_schema(
                active.checkpoint_database_url,
                active.checkpoint_schema,
            )
            await pool.open(wait=True)
            checkpointer = AsyncPostgresSaver(pool)
            await checkpointer.setup()
            app.state.settings = active
            app.state.domain_client = client
            app.state.checkpoint_pool = pool
            app.state.graph = build_graph(settings=active, client=client, checkpointer=checkpointer)
            yield
        finally:
            await http_client.aclose()
            await pool.close()

    app = FastAPI(title="Ops Agent", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active.cors_origins.split(","),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/chat", response_model=ChatResponse)
    async def chat(body: ChatRequest, request: Request) -> ChatResponse:
        current: Settings = request.app.state.settings
        thread_id = str(body.thread_id)
        config: RunnableConfig = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": current.recursion_limit,
        }
        try:
            result = await request.app.state.graph.ainvoke(
                {
                    "messages": [HumanMessage(content=body.message)],
                    "tool_rounds": 0,
                    "soft_limit_reached": False,
                },
                config=config,
            )
        except GraphRecursionError as exc:
            logger.exception("LangGraph recursion limit reached")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The agent could not complete this request safely.",
            ) from exc
        except Exception as exc:
            logger.exception("Unexpected graph or checkpointer failure")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The agent is temporarily unavailable.",
            ) from exc

        final = next(
            (
                message
                for message in reversed(result["messages"])
                if isinstance(message, AIMessage) and not message.tool_calls
            ),
            None,
        )
        if final is None or not (answer := message_text(final)):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The agent did not produce a final answer.",
            )
        return ChatResponse(
            answer=answer,
            thread_id=body.thread_id,
            tool_rounds=result.get("tool_rounds", 0),
            soft_limit_reached=result.get("soft_limit_reached", False),
        )

    return app


app = create_app()
