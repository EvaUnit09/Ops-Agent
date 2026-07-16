from __future__ import annotations

import json
import os
import urllib.request

import pytest

pytestmark = pytest.mark.live


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_EVALS") != "1",
    reason="set RUN_LIVE_EVALS=1 to spend provider credits",
)
def test_flagship_live_response_contract() -> None:
    agent_url = os.getenv("AGENT_PUBLIC_URL", "http://localhost:8001").rstrip("/")
    thread_id = "995cdf7d-d452-4c23-83f9-88aef870ca1f"
    request = urllib.request.Request(
        f"{agent_url}/chat",
        data=json.dumps(
            {
                "message": (
                    "Which Marketing employees currently have laptops that have "
                    "not synced in at least 30 days?"
                ),
                "thread_id": thread_id,
            }
        ).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.load(response)
    assert set(payload) == {
        "answer",
        "thread_id",
        "tool_rounds",
        "soft_limit_reached",
    }
    assert payload["thread_id"] == thread_id
    assert payload["answer"].strip()
    assert payload["tool_rounds"] >= 1
    assert payload["soft_limit_reached"] is False
