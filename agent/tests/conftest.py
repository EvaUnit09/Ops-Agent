"""Shared pytest fixtures for the agent test suite.

conftest.py is a special filename: pytest finds it automatically and makes
every fixture defined here available to all test files in this directory —
no imports needed. A test gets a fixture simply by naming it as a parameter.

Setting ANTHROPIC_API_KEY / CHECKPOINT_DATABASE_URL here, before any test
module imports app.main, matters because app.main builds a module-level
`app = create_app()` for uvicorn to serve — importing that module without
those two required settings present would fail Settings() validation before
a single test ran.

Governed by:
  §"Six canonical tool contracts / All tool wrappers share these behaviors"
    in 00-roadmap-and-contracts.md
"""

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("CHECKPOINT_DATABASE_URL", "postgresql://test:test@localhost/test")

from collections.abc import Sequence  # noqa: E402
from typing import Any  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402
from langchain_core.messages import AIMessage, BaseMessage  # noqa: E402

from app.api_client import DomainApiClient  # noqa: E402
from app.config import Settings  # noqa: E402

# ---------------------------------------------------------------------------
# Envelope helpers
# ---------------------------------------------------------------------------
# Every fake response a test scripts must look like the real API's
# {data, error, meta} envelope. Writing that dict by hand in every test is
# repetitive and easy to typo, so these two plain functions (not fixtures —
# they need no pytest machinery) build the two canonical shapes.


def success_envelope(data, count: int | None = None, limit: int | None = 50) -> dict:
    """Build a successful envelope: data populated, error null.

    `count` defaults to len(data) for lists, 1 otherwise — mirroring the
    real API's meta.count rules.
    """
    if count is None:
        count = len(data) if isinstance(data, list) else 1
    return {"data": data, "error": None, "meta": {"count": count, "limit": limit}}


def error_envelope(code: str, message: str) -> dict:
    """Build a failure envelope: data null, error populated with a stable code."""
    return {
        "data": None,
        "error": {"code": code, "message": message},
        "meta": {"count": 0, "limit": None},
    }


# ---------------------------------------------------------------------------
# The client factory fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def make_client():
    """Factory fixture: returns a function that builds a DomainApiClient
    wired to a fake API.

    Why a factory instead of a ready-made client? Because each test needs a
    DIFFERENT fake API (one wants a 404, another wants 503-then-200). The
    test declares `make_client` as a parameter, receives this factory, and
    calls it with a handler describing the fake API for that one test:

        def handler(request):
            return httpx.Response(404, json=error_envelope("not_found", "..."))

        client = make_client(handler)

    How the fake works: httpx.MockTransport replaces the network layer.
    Every request the client sends is handed to `handler`, and whatever
    httpx.Response the handler returns is what the client "receives".
    All of DomainApiClient's real logic (URL building, envelope validation,
    retry, error mapping) still runs — only the wire is fake. No server,
    no network, no port 8000.
    """

    def _make(handler) -> DomainApiClient:
        # MockTransport: the fake wire. Routes every outgoing request to `handler`.
        transport = httpx.MockTransport(handler)

        # A real httpx.AsyncClient, but with the fake transport plugged in.
        # base_url is required so relative paths like "/assets/999" resolve;
        # "http://testserver" is a conventional dummy — nothing is ever
        # actually contacted.
        http = httpx.AsyncClient(transport=transport, base_url="http://testserver")

        # Dependency injection: DomainApiClient RECEIVES its AsyncClient
        # rather than creating one internally. That one design choice is
        # what makes this entire file possible — in production, main.py's
        # lifespan hands it a real client; in tests, we hand it this fake.
        return DomainApiClient(http)

    # The fixture returns the factory itself; the test calls it.
    return _make


# ---------------------------------------------------------------------------
# Higher-level fakes for tool/graph/chat tests
# ---------------------------------------------------------------------------


class FakeDomainClient:
    """A DomainApiClient stand-in that returns scripted responses by path.

    Unlike `make_client`, this never touches httpx at all — it just records
    every (path, params) call and looks up a canned response, defaulting to
    an empty list for any path a test doesn't care about.
    """

    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        self.calls.append((path, params or {}))
        return self.responses.get(path, [])


class ScriptedModel:
    """A fake chat model that returns pre-scripted AIMessages in order.

    `bind_tools` just records the tool names and returns self, so the same
    fake serves as both the tools-bound model and the finalizer's base model.
    """

    def __init__(self, responses: Sequence[AIMessage]) -> None:
        self.responses = list(responses)
        self.seen: list[list[BaseMessage]] = []

    def bind_tools(self, tools: Sequence[Any]) -> "ScriptedModel":
        self.tool_names = [tool.name for tool in tools]
        return self

    async def ainvoke(self, messages: list[BaseMessage], config: Any = None) -> AIMessage:
        self.seen.append(messages)
        if not self.responses:
            raise AssertionError("unexpected model call")
        return self.responses.pop(0)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        ANTHROPIC_API_KEY="test",
        ANTHROPIC_MODEL="test-model",
        API_BASE_URL="http://domain.test",
        CHECKPOINT_DATABASE_URL="postgresql://test:test@db/test",
        CHECKPOINT_SCHEMA="agent_checkpoints",
        API_RETRY_DELAY_SECONDS=0,
    )