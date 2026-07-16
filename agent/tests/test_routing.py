from langchain_core.messages import AIMessage
from langgraph.graph import END

from app.routing import route_after_model, route_after_tools


def test_model_routes_by_tool_calls() -> None:
    call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_users_by_department",
                "args": {"department": "Engineering"},
                "id": "call-1",
                "type": "tool_call",
            }
        ],
    )
    assert route_after_model({"messages": [call]}) == "tools"
    assert route_after_model({"messages": [AIMessage(content="done")]}) == END


def test_soft_limit_routes_to_finalizer() -> None:
    assert (
        route_after_tools({"messages": [], "tool_rounds": 4, "soft_limit_reached": True})
        == "finalize"
    )


def test_below_soft_limit_routes_to_model() -> None:
    assert (
        route_after_tools({"messages": [], "tool_rounds": 1, "soft_limit_reached": False})
        == "model"
    )
