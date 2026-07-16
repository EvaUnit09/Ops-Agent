from __future__ import annotations

import json
import os
import subprocess
import time
import unittest
import urllib.error
import urllib.request
import uuid
from typing import Any


AGENT_URL = os.getenv("AGENT_PUBLIC_URL", "http://localhost:8001").rstrip("/")


def post_chat(message: str, thread_id: str, timeout: float = 120) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{AGENT_URL}/chat",
        data=json.dumps({"message": message, "thread_id": thread_id}).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    assert set(payload) == {
        "answer",
        "thread_id",
        "tool_rounds",
        "soft_limit_reached",
    }, f"chat contract drift: {payload!r}"
    return payload


def compose(*args: str) -> None:
    subprocess.run(["docker", "compose", *args], check=True)


class LiveStackTests(unittest.TestCase):
    def test_01_flagship_query(self) -> None:
        thread_id = str(uuid.uuid4())
        result = post_chat(
            "Which Marketing employees currently have laptops that have not "
            "synced in at least 30 days?",
            thread_id,
        )
        self.assertEqual(result["thread_id"], thread_id)
        self.assertGreaterEqual(result["tool_rounds"], 1)
        self.assertFalse(result["soft_limit_reached"])
        self.assertTrue(result["answer"].strip())

    def test_02_multi_turn_survives_agent_restart(self) -> None:
        thread_id = str(uuid.uuid4())
        first = post_chat(
            "Find stale laptops assigned to Marketing. "
            "Remember that my follow-up is about this same group.",
            thread_id,
        )
        self.assertTrue(first["answer"].strip())

        compose("restart", "agent")
        deadline = time.monotonic() + 90
        while True:
            try:
                follow_up = post_chat(
                    "Which department did I ask about?", thread_id
                )
                break
            except (OSError, urllib.error.URLError):
                if time.monotonic() >= deadline:
                    raise
                time.sleep(2)
        answer = follow_up["answer"].casefold()
        self.assertIn("marketing", answer)

    def test_03_api_outage_is_handled(self) -> None:
        thread_id = str(uuid.uuid4())
        compose("stop", "api")
        try:
            result = post_chat(
                "Find stale laptops assigned to Marketing.", thread_id
            )
            self.assertTrue(result["answer"].strip())
            text = result["answer"].casefold()
            self.assertTrue(
                any(
                    word in text
                    for word in ("unavailable", "couldn't", "cannot", "try again")
                ),
                result["answer"],
            )
        finally:
            compose("start", "api")
