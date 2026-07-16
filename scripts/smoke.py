#!/usr/bin/env python3
"""Health and read-only contract probes using only the standard library."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    timeout: float = 5.0,
) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        raw = error.read().decode()
        try:
            return error.code, json.loads(raw)
        except json.JSONDecodeError:
            return error.code, raw


def wait_for_health(base_url: str, deadline_seconds: int) -> None:
    deadline = time.monotonic() + deadline_seconds
    last_error = "not attempted"
    while time.monotonic() < deadline:
        try:
            status, payload = request_json(base_url, "/health")
            if status == 200 and isinstance(payload, dict):
                return
            last_error = f"HTTP {status}: {payload!r}"
        except (OSError, ValueError) as error:
            last_error = str(error)
        time.sleep(1)
    raise AssertionError(f"{base_url}/health was not ready: {last_error}")


def assert_domain_reads(api_url: str) -> None:
    health_status, health = request_json(api_url, "/health")
    assert health_status == 200, f"GET /health returned {health_status}: {health!r}"
    assert health == {
        "data": {"status": "ok", "database": "ok"},
        "error": None,
        "meta": {"count": 1, "limit": None},
    }

    checks = (
        (
            "/assets/search?"
            + urllib.parse.urlencode(
                {
                    "category": "laptop",
                    "status": "checked_out",
                    "region": "emea",
                    "limit": 5,
                }
            ),
            False,
        ),
        ("/assets/stale?stale_days=30&category=laptop&limit=5", True),
        (
            "/assets/by-department?"
            + urllib.parse.urlencode(
                {
                    "department": "Marketing",
                    "category": "laptop",
                    "stale_days": 30,
                    "limit": 5,
                }
            ),
            True,
        ),
        ("/users/search?department=Marketing&limit=5", True),
        ("/users/search?department=Marketing&q=example.com&limit=5", True),
    )
    for path, expect_seeded_rows in checks:
        status, payload = request_json(api_url, path)
        assert status == 200, f"GET {path} returned {status}: {payload!r}"
        assert isinstance(payload, dict), f"GET {path} must return an envelope"
        assert set(payload) == {"data", "error", "meta"}, (
            f"GET {path} envelope drift: {payload!r}"
        )
        assert isinstance(payload["data"], list), f"GET {path} data must be a list"
        assert payload["error"] is None, f"GET {path} returned an error envelope"
        assert isinstance(payload["meta"], dict)
        assert set(payload["meta"]) == {"count", "limit"}
        if expect_seeded_rows:
            assert payload["data"], f"guaranteed seed fixture missing for GET {path}"


def assert_chat_contract(agent_url: str, thread_id: str) -> None:
    status, payload = request_json(
        agent_url,
        "/chat",
        method="POST",
        body={
            "message": (
                "Which Marketing employees currently have laptops that have "
                "not synced in at least 30 days?"
            ),
            "thread_id": thread_id,
        },
        timeout=90,
    )
    assert status == 200, f"POST /chat returned {status}: {payload!r}"
    assert isinstance(payload, dict)
    assert set(payload) == {
        "answer",
        "thread_id",
        "tool_rounds",
        "soft_limit_reached",
    }, f"unexpected chat keys: {sorted(payload)}"
    assert isinstance(payload["answer"], str) and payload["answer"].strip()
    assert payload["thread_id"] == thread_id
    assert isinstance(payload["tool_rounds"], int) and payload["tool_rounds"] >= 0
    assert isinstance(payload["soft_limit_reached"], bool)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--api-url", default=os.getenv("API_PUBLIC_URL", "http://localhost:8000")
    )
    parser.add_argument(
        "--agent-url",
        default=os.getenv("AGENT_PUBLIC_URL", "http://localhost:8001"),
    )
    parser.add_argument("--deadline", type=int, default=120)
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Call the real model; never use this in pull-request CI.",
    )
    parser.add_argument(
        "--thread-id", default="7a0bb26f-1bd8-4c45-944c-86d884f735f6"
    )
    args = parser.parse_args()

    wait_for_health(args.api_url, args.deadline)
    wait_for_health(args.agent_url, args.deadline)
    assert_domain_reads(args.api_url)
    if args.chat:
        assert_chat_contract(args.agent_url, args.thread_id)
    print("smoke checks passed")


if __name__ == "__main__":
    main()
