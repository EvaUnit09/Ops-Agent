from tests.evals.rubric import score_tool_plan


def test_scripted_model_plan_meets_full_rubric() -> None:
    # Feed this same scripted payload through phase 2's injected fake model;
    # its model-node test must also prove IDs and arguments survive unchanged.
    tool_calls = [
        {
            "id": "call_flagship",
            "name": "get_assets_by_department",
            "args": {
                "department": "Marketing",
                "category": "laptop",
                "stale_days": 30,
            },
        }
    ]
    score = score_tool_plan(tool_calls)
    assert score.total == 5, score


def test_unbounded_or_mutating_plan_is_rejected() -> None:
    unbounded = [
        {
            "id": "call_all",
            "name": "get_assets_by_department",
            "args": {"department": "Marketing"},
        }
    ]
    mutation = [{"id": "bad", "name": "update_asset", "args": {"asset_id": 1}}]
    assert score_tool_plan(unbounded).total < 5
    assert not score_tool_plan(mutation).read_only_selection
    assert not score_tool_plan(mutation).no_invented_mutation
