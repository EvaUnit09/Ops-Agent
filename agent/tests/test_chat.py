from typing import Any

import httpx
from langchain_core.messages import AIMessage
from langgraph.errors import GraphRecursionError

from app.main import create_app


class StubGraph:
    async def ainvoke(
        self, graph_input: dict[str, Any], *, config: dict[str, Any]
    ) -> dict[str, Any]:
        self.input, self.config = graph_input, config
        return {
            "messages": [
                *graph_input["messages"],
                AIMessage(content=[{"type": "text", "text": "Two laptops match."}]),
            ],
            "tool_rounds": 2,
            "soft_limit_reached": False,
        }


class RecursionErrorGraph:
    async def ainvoke(
        self, graph_input: dict[str, Any], *, config: dict[str, Any]
    ) -> dict[str, Any]:
        raise GraphRecursionError("recursion limit reached")


class UnexpectedFailureGraph:
    async def ainvoke(
        self, graph_input: dict[str, Any], *, config: dict[str, Any]
    ) -> dict[str, Any]:
        raise RuntimeError("upstream model provider error")


class NoFinalAnswerGraph:
    async def ainvoke(
        self, graph_input: dict[str, Any], *, config: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "messages": [
                *graph_input["messages"],
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "search_assets",
                            "args": {},
                            "id": "call-unfinished",
                            "type": "tool_call",
                        }
                    ],
                ),
            ],
            "tool_rounds": 1,
            "soft_limit_reached": False,
        }


async def test_chat_contract_config_reset_and_cors(settings) -> None:
    graph = StubGraph()
    app = create_app(settings)
    app.state.settings, app.state.graph = settings, graph
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/chat",
            json={
                "message": "Find laptops",
                "thread_id": "44444444-4444-4444-8444-444444444444",
            },
            headers={"Origin": "http://localhost:5173"},
        )
    assert response.status_code == 200
    assert response.json() == {
        "answer": "Two laptops match.",
        "thread_id": "44444444-4444-4444-8444-444444444444",
        "tool_rounds": 2,
        "soft_limit_reached": False,
    }
    assert graph.input["tool_rounds"] == 0
    assert graph.config == {
        "configurable": {"thread_id": "44444444-4444-4444-8444-444444444444"},
        "recursion_limit": 25,
    }
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


async def test_blank_message_is_rejected(settings) -> None:
    app = create_app(settings)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/chat",
            json={"message": "   ", "thread_id": "55555555-5555-4555-8555-555555555555"},
        )
    assert response.status_code == 422


async def test_non_uuid_thread_id_is_rejected(settings) -> None:
    app = create_app(settings)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/chat",
            json={"message": "Find laptops", "thread_id": "not-a-uuid"},
        )
    assert response.status_code == 422


async def test_recursion_limit_returns_503(settings) -> None:
    app = create_app(settings)
    app.state.settings, app.state.graph = settings, RecursionErrorGraph()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/chat",
            json={
                "message": "Find laptops",
                "thread_id": "66666666-6666-4666-8666-666666666666",
            },
        )
    assert response.status_code == 503


async def test_unexpected_graph_failure_returns_503_without_leaking_detail(settings) -> None:
    app = create_app(settings)
    app.state.settings, app.state.graph = settings, UnexpectedFailureGraph()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/chat",
            json={
                "message": "Find laptops",
                "thread_id": "88888888-8888-4888-8888-888888888888",
            },
        )
    assert response.status_code == 503
    assert "upstream model provider error" not in response.text


async def test_missing_final_answer_returns_503(settings) -> None:
    app = create_app(settings)
    app.state.settings, app.state.graph = settings, NoFinalAnswerGraph()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/chat",
            json={
                "message": "Find laptops",
                "thread_id": "77777777-7777-4777-8777-777777777777",
            },
        )
    assert response.status_code == 503
