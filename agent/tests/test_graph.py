import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from app.graph import build_graph
from tests.conftest import FakeDomainClient, ScriptedModel


async def test_tool_call_id_round_and_answer(settings) -> None:
    model = ScriptedModel(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_users_by_department",
                        "args": {"department": "Engineering"},
                        "id": "call-123",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="Ada is in Engineering."),
        ]
    )
    graph = build_graph(
        settings=settings,
        client=FakeDomainClient({"/users/search": [{"id": 5, "name": "Ada"}]}),
        checkpointer=InMemorySaver(),
        model=model,
    )
    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="Who is in Engineering?")],
            "tool_rounds": 0,
            "soft_limit_reached": False,
        },
        config={
            "configurable": {"thread_id": "11111111-1111-4111-8111-111111111111"},
            "recursion_limit": 25,
        },
    )
    tool_message = next(x for x in result["messages"] if isinstance(x, ToolMessage))
    assert tool_message.tool_call_id == "call-123"
    assert json.loads(tool_message.content)["count"] == 1
    assert result["messages"][-1].content == "Ada is in Engineering."
    assert result["tool_rounds"] == 1
    assert result["soft_limit_reached"] is False


async def test_soft_cap_executes_tool_then_finalizes(settings) -> None:
    settings = settings.model_copy(update={"max_tool_rounds": 1})
    model = ScriptedModel(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_assets",
                        "args": {"category": "laptop"},
                        "id": "call-cap",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="One laptop found; the lookup limit stopped more work."),
        ]
    )
    graph = build_graph(
        settings=settings,
        client=FakeDomainClient({"/assets/search": [{"id": 1}]}),
        checkpointer=InMemorySaver(),
        model=model,
    )
    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="Investigate laptop history")],
            "tool_rounds": 0,
            "soft_limit_reached": False,
        },
        config={
            "configurable": {"thread_id": "22222222-2222-4222-8222-222222222222"},
            "recursion_limit": 25,
        },
    )
    assert result["tool_rounds"] == 1
    assert result["soft_limit_reached"] is True
    assert "lookup limit" in result["messages"][-1].content


async def test_same_thread_resumes_messages_and_resets_counter(settings) -> None:
    model = ScriptedModel([AIMessage(content="first"), AIMessage(content="second")])
    graph = build_graph(
        settings=settings,
        client=FakeDomainClient(),
        checkpointer=InMemorySaver(),
        model=model,
    )
    config = {
        "configurable": {"thread_id": "33333333-3333-4333-8333-333333333333"},
        "recursion_limit": 25,
    }
    for text in ("First question", "Follow-up"):
        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content=text)],
                "tool_rounds": 0,
                "soft_limit_reached": False,
            },
            config=config,
        )
    human_text = [x.content for x in model.seen[1] if isinstance(x, HumanMessage)]
    assert human_text == ["First question", "Follow-up"]
    assert result["tool_rounds"] == 0
