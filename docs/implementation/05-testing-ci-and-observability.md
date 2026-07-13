# Phase 5 — Testing, CI, release images, and observability

This phase closes the handbook. It adds checks spanning service boundaries, deterministic pull-request CI, immutable container publishing, and a safe trace record.

Canonical contracts:

- API: `http://localhost:8000`; agent: `http://localhost:8001`
- both Python services expose `GET /health`
- `POST /chat` accepts
  `{"message":"...","thread_id":"7a0bb26f-1bd8-4c45-944c-86d884f735f6"}`
- `/chat` returns exactly `answer`, `thread_id`, `tool_rounds`, and `soft_limit_reached`
- the eight domain routes and six read-only tools are those defined in phases 0–2
- every concrete `thread_id` in this guide is a UUID string
- domain API responses use the `data` / `error` / `meta` envelope

## 1. Test boundaries and target files

Keep three classes separate:

1. **PR tests:** API tests, mocked agent/model tests, frontend tests, image builds, and no-model smoke checks. No Anthropic or LangSmith credential is present.
2. **Stack acceptance:** Compose health and domain reads. Chat stays disabled unless `RUN_LIVE_EVALS=1`.
3. **Live evals:** real-model, potentially traced checks before a demo/release. They are not merge gates because output, latency, provider availability, and cost vary.

Type these files after phases 1–4:

```text
.github/workflows/ci.yml
.github/workflows/deploy.yml
agent/tests/evals/__init__.py
agent/tests/__init__.py
agent/tests/evals/rubric.py
agent/tests/evals/test_model_plan_mocked.py
agent/tests/evals/test_live_model.py
scripts/smoke.py
scripts/e2e.sh
tests/e2e/domain_fingerprint.sql
tests/e2e/test_live_stack.py
project_log.md
```

The logging helper in section 7 is optional, not baseline.

## 2. Dependency-free smoke probe

### `scripts/smoke.py`

```python
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
```

The default path never invokes Claude. `/assets/search` has no text query:
`category`, `status`, and `region` are optional filters. `/users/search` requires
`department` and accepts optional `q`; omitting `q` above proves the department-only
contract, while `q=example.com` proves the bounded text refinement without inventing
a person-specific fixture. Phase 1 guarantees at least one stale laptop currently
assigned to Marketing, so both stale and by-department checks require rows without
hard-coding a fabricated asset tag. Run:

```bash
chmod +x scripts/smoke.py
python3 scripts/smoke.py
```

## 3. Authoritative read-only fingerprint and E2E runner

Bounded HTTP searches cannot prove every row stayed unchanged. The fingerprint therefore reads all domain rows directly in a read-only transaction. This is test infrastructure only; application code still reaches domain data solely through the API.

### `tests/e2e/domain_fingerprint.sql`

```sql
\set ON_ERROR_STOP on
BEGIN TRANSACTION READ ONLY;

COPY (
    SELECT row_value
    FROM (
        SELECT
            'asset|' || id::text || '|' || tag || '|' || category::text || '|' ||
            model || '|' || status::text || '|' || region::text || '|' ||
            to_char(last_synced_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US')
            AS row_value
        FROM public.assets
        UNION ALL
        SELECT
            'user|' || id::text || '|' || name || '|' || email || '|' ||
            department::text
        FROM public.users
        UNION ALL
        SELECT
            'checkout|' || id::text || '|' || asset_id::text || '|' ||
            user_id::text || '|' ||
            to_char(checked_out_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US') ||
            '|' || coalesce(
                to_char(checked_in_at AT TIME ZONE 'UTC',
                        'YYYY-MM-DD"T"HH24:MI:SS.US'),
                ''
            )
        FROM public.checkouts
    ) rows
    ORDER BY row_value
) TO STDOUT;

ROLLBACK;
```

Explicit ordering, UTC formatting, enum text, and separators make the digest repeatable.

### `scripts/e2e.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
compose=(docker compose)
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-opsagent-e2e}"

cleanup() {
  if [[ "${KEEP_STACK:-0}" != "1" ]]; then
    "${compose[@]}" down --volumes --remove-orphans
  fi
}
trap cleanup EXIT

fingerprint() {
  "${compose[@]}" exec -T db \
    sh -ec 'exec psql -X --no-psqlrc \
      --username="$POSTGRES_USER" \
      --dbname="$POSTGRES_DB"' \
    < tests/e2e/domain_fingerprint.sql \
    | shasum -a 256 | awk '{print $1}'
}

[[ -f .env ]] || cp .env.example .env

# Health constructs settings/model clients but never invokes a model.
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-ci-not-a-real-key}"
export LANGCHAIN_TRACING_V2="${LANGCHAIN_TRACING_V2:-false}"

"${compose[@]}" up --detach --build --wait --wait-timeout 180
python3 scripts/smoke.py

before="$(fingerprint)"
after="$(fingerprint)"
[[ "$before" == "$after" ]] || {
  echo "domain changed during read-only smoke checks" >&2
  exit 1
}

if [[ "${RUN_LIVE_EVALS:-0}" == "1" ]]; then
  [[ "$ANTHROPIC_API_KEY" != "ci-not-a-real-key" ]] || {
    echo "RUN_LIVE_EVALS=1 requires a real ANTHROPIC_API_KEY" >&2
    exit 2
  }
  python3 -m unittest -v tests.e2e.test_live_stack
  live_after="$(fingerprint)"
  [[ "$before" == "$live_after" ]] || {
    echo "live agent changed domain data" >&2
    exit 1
  }
fi

echo "E2E acceptance passed; domain fingerprint: $before"
```

```bash
chmod +x scripts/e2e.sh
```

`KEEP_STACK=1` preserves a failed stack. The default volume removal means each run proves migration and deterministic seed startup from empty storage.

### `tests/e2e/test_live_stack.py`

```python
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
```

The numeric names make shared-container ordering explicit. An outage must return useful handled prose, never HTTP 500 or invented inventory. The runner's final fingerprint proves all live scenarios remained read-only.

## 4. Model-node evaluation rubric

The model node must emit either a final `AIMessage` or valid tool calls. Score five binary criteria:

- calls only the six approved read-only tools;
- emits IDs and mapping arguments;
- answers the flagship efficiently with bounded department/category/staleness filters;
- invents no mutation, SQL, or generic HTTP tool;
- emits no duplicate identical calls.

Mocked fixtures must score 5/5. Live runs may score 4/5 only when the missing point is efficiency; read-only selection and schema validity are mandatory.

### `agent/tests/__init__.py`

```python
"""Agent test package."""
```

### `agent/tests/evals/__init__.py`

```python
"""Deterministic rubric helpers and opt-in live evaluations."""
```

### `agent/tests/evals/rubric.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


APPROVED_TOOLS = {
    "search_assets",
    "find_stale_assets",
    "get_assets_by_department",
    "get_checkout_history",
    "get_user_assets",
    "search_users_by_department",
}


@dataclass(frozen=True)
class Score:
    read_only_selection: bool
    schema_validity: bool
    flagship_efficiency: bool
    no_invented_mutation: bool
    loop_discipline: bool

    @property
    def total(self) -> int:
        return sum(
            (
                self.read_only_selection,
                self.schema_validity,
                self.flagship_efficiency,
                self.no_invented_mutation,
                self.loop_discipline,
            )
        )


def score_tool_plan(tool_calls: list[dict[str, Any]]) -> Score:
    names = [call.get("name") for call in tool_calls]
    approved = bool(tool_calls) and all(name in APPROVED_TOOLS for name in names)
    schema = all(
        isinstance(call.get("id"), str)
        and bool(call["id"])
        and isinstance(call.get("args"), dict)
        for call in tool_calls
    )
    flagship = [
        call
        for call in tool_calls
        if call.get("name") == "get_assets_by_department"
    ]
    efficient = len(flagship) == 1 and {
        "department": "Marketing",
        "category": "laptop",
        "stale_days": 30,
    }.items() <= flagship[0]["args"].items()
    mutation_words = ("create", "update", "delete", "assign", "sql", "http")
    no_mutation = all(
        not any(word in str(name).casefold() for word in mutation_words)
        for name in names
    )
    signatures = [
        (call.get("name"), repr(sorted(call.get("args", {}).items())))
        for call in tool_calls
    ]
    disciplined = bool(tool_calls) and len(signatures) == len(set(signatures))
    return Score(approved, schema, efficient, no_mutation, disciplined)
```

### `agent/tests/evals/test_model_plan_mocked.py`

```python
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
```

### `agent/tests/evals/test_live_model.py`

```python
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
```

Register and use the marker in `agent/pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = ["live: calls a running stack and may spend provider credits"]
```

```bash
uv run pytest -m "not live"
RUN_LIVE_EVALS=1 uv run pytest -m live agent/tests/evals/test_live_model.py
```

Exact prose is never a live assertion. Routing and payload preservation belong in the scripted model-node test; live checks score behavior and retain a trace.

## 5. Path-aware pull-request CI

### `.github/workflows/ci.yml`

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read
  pull-requests: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  changes:
    runs-on: ubuntu-latest
    outputs:
      api: ${{ steps.filter.outputs.api }}
      agent: ${{ steps.filter.outputs.agent }}
      frontend: ${{ steps.filter.outputs.frontend }}
      stack: ${{ steps.filter.outputs.stack }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            api:
              - 'api/**'
              - 'tests/e2e/**'
              - 'scripts/smoke.py'
              - '.github/workflows/ci.yml'
            agent:
              - 'agent/**'
              - 'tests/e2e/**'
              - 'scripts/**'
              - '.github/workflows/ci.yml'
            frontend:
              - 'frontend/**'
              - '.github/workflows/ci.yml'
            stack:
              - 'api/**'
              - 'agent/**'
              - 'frontend/**'
              - 'tests/e2e/**'
              - 'scripts/**'
              - 'docker-compose.yml'
              - '.env.example'
              - '.github/workflows/ci.yml'

  api:
    needs: changes
    if: needs.changes.outputs.api == 'true'
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: opsagent
          POSTGRES_PASSWORD: localdev
          POSTGRES_DB: opsagent_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U opsagent -d opsagent_test"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 12
    env:
      DATABASE_URL: postgresql+psycopg://opsagent:localdev@localhost:5432/opsagent_test
      TEST_DATABASE_URL: postgresql+psycopg://opsagent:localdev@localhost:5432/opsagent_test
    defaults:
      run:
        working-directory: api
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
          cache-dependency-glob: api/uv.lock
      - run: uv sync --locked --all-groups
      - run: uv run ruff check .
      - run: uv run python -m compileall app alembic tests
      - name: Verify PostgreSQL readiness
        run: pg_isready --host=localhost --username=opsagent --dbname=opsagent_test
      - run: uv run alembic upgrade head
      - run: uv run pytest --cov=app --cov-report=term-missing

  agent:
    needs: changes
    if: needs.changes.outputs.agent == 'true'
    runs-on: ubuntu-latest
    env:
      LANGCHAIN_TRACING_V2: "false"
    defaults:
      run:
        working-directory: agent
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
          cache-dependency-glob: agent/uv.lock
      - run: uv sync --locked --all-groups
      - run: uv run ruff check .
      - run: uv run pytest --cov=app --cov-report=term-missing -m "not live"

  frontend:
    needs: changes
    if: needs.changes.outputs.frontend == 'true'
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run typecheck
      - run: npm run lint
      - run: npm test
      - run: npm run build

  clean-clone:
    needs: changes
    if: needs.changes.outputs.stack == 'true'
    runs-on: ubuntu-latest
    timeout-minutes: 20
    env:
      ANTHROPIC_API_KEY: ci-not-a-real-key
      LANGCHAIN_TRACING_V2: "false"
    steps:
      - uses: actions/checkout@v4
      - run: cp .env.example .env
      - run: docker compose config --quiet
      - run: docker compose build
      - run: docker compose up --detach --wait --wait-timeout 180
      - run: python3 scripts/smoke.py
      - name: Show container diagnostics
        if: failure()
        run: docker compose ps --all && docker compose logs --no-color
      - name: Tear down
        if: always()
        run: docker compose down --volumes --remove-orphans

  required:
    name: Required CI
    if: always()
    needs: [changes, api, agent, frontend, clean-clone]
    runs-on: ubuntu-latest
    steps:
      - name: Verify selected jobs
        env:
          RESULTS: ${{ join(needs.*.result, ',') }}
        run: |
          case ",$RESULTS," in
            *,failure,*|*,cancelled,*) exit 1 ;;
            *) exit 0 ;;
          esac
```

Service-local edits run local tests; shared E2E paths fan into both backends; operational paths run clean-clone acceptance. Docs-only changes run `changes` plus the stable `Required CI` branch-protection check. Conditional jobs may skip without making the required check disappear.

The public placeholder is not a secret; it only satisfies eager settings validation
while the clean-clone job starts the agent. No PR command calls `/chat`, no GitHub
model or LangSmith secret is referenced, and tracing is forced off. The API and agent
jobs both use Python 3.13 and the actual Phase 1–2 `dev` dependency groups through
`uv sync --locked --all-groups`; there is no undefined `[test]` extra. The API uses a
real PostgreSQL 16 `opsagent_test` database, with the documented `opsagent` role and
`localdev` password. Its `_test` suffix satisfies the destructive-test guard.
`pg_isready` and `uv run alembic upgrade head` separately prove readiness and
migration before pytest. Commit both `uv.lock` files and the frontend's
`package-lock.json`; locked uv sync and `npm ci` intentionally fail on manifest drift.

For supply-chain hardening, pin third-party actions to reviewed commit SHAs and update them with Dependabot. Tags remain here for readability.

## 6. GHCR publishing

### `.github/workflows/deploy.yml`

```yaml
name: Publish images

on:
  push:
    branches: [main]
    tags: ['v*.*.*']
    paths:
      - 'api/**'
      - 'agent/**'
      - 'frontend/**'
      - 'docker-compose.yml'
      - '.github/workflows/deploy.yml'
  workflow_dispatch:

permissions:
  contents: read
  packages: write
  id-token: write
  attestations: write

concurrency:
  group: publish-${{ github.ref }}
  cancel-in-progress: false

jobs:
  publish:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        include:
          - service: api
            context: ./api
          - service: agent
            context: ./agent
          - service: frontend
            context: ./frontend
    steps:
      - uses: actions/checkout@v4
      - name: Derive lowercase image name
        id: image
        shell: bash
        run: |
          owner="${GITHUB_REPOSITORY_OWNER,,}"
          echo "name=ghcr.io/${owner}/ops-agent-${{ matrix.service }}" >> "$GITHUB_OUTPUT"
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/metadata-action@v5
        id: meta
        with:
          images: ${{ steps.image.outputs.name }}
          tags: |
            type=ref,event=branch
            type=ref,event=tag
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha,prefix=sha-,format=long
            type=raw,value=latest,enable=${{ startsWith(github.ref, 'refs/tags/v') }}
          labels: |
            org.opencontainers.image.source=${{ github.server_url }}/${{ github.repository }}
            org.opencontainers.image.revision=${{ github.sha }}
      - uses: docker/build-push-action@v6
        id: build
        with:
          context: ${{ matrix.context }}
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha,scope=${{ matrix.service }}
          cache-to: type=gha,mode=max,scope=${{ matrix.service }}
          provenance: true
          sbom: true
      - name: Attest image
        uses: actions/attest-build-provenance@v2
        with:
          subject-name: ${{ steps.image.outputs.name }}
          subject-digest: ${{ steps.build.outputs.digest }}
          push-to-registry: true
```

All three images publish together as a coherent release set; service-selective publishing could leave moving `main` tags at different commits. Workflow paths suppress docs-only releases.

- `sha-<40-char commit>` is immutable and preferred for deploy/rollback.
- `main` moves with integration.
- `v1.2.3` and `1.2` are release conveniences.
- `latest` appears only on a semantic version tag.

GHCR owners must be lowercase. Record the image digest—not only a moving tag—in `project_log.md`.

## 7. Optional structured logging

Uvicorn access logs plus LangSmith suffice initially. If source/trace correlation is needed, place this identical helper at both `api/app/observability.py` and `agent/app/observability.py`. Duplication keeps separately built services independent.

```python
from __future__ import annotations

import contextvars
import json
import logging
import re
import time
import uuid
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send


_request_id = contextvars.ContextVar("request_id", default="-")
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_REDACT = {
    "authorization", "cookie", "api_key", "message", "answer",
    "tool_input", "tool_output",
}


def request_id() -> str:
    return _request_id.get()


def _safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if key.casefold() in _REDACT else _safe(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "request_id": request_id(),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(_safe(fields))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_json_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = logging.getLogger("http")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {
            key.decode("latin-1").casefold(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        supplied = headers.get("x-request-id", "")
        current = supplied if _SAFE_ID.fullmatch(supplied) else str(uuid.uuid4())
        token = _request_id.set(current)
        status = 500
        started = time.monotonic()

        async def send_with_context(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message["headers"] = [
                    *message.get("headers", []),
                    (b"x-request-id", current.encode("ascii")),
                ]
            await send(message)

        try:
            await self.app(scope, receive, send_with_context)
        finally:
            self.logger.info(
                "request.completed",
                extra={
                    "fields": {
                        "method": scope["method"],
                        "path": scope["path"],
                        "status_code": status,
                        "duration_ms": round((time.monotonic() - started) * 1000, 1),
                    }
                },
            )
            _request_id.reset(token)
```

Configure it once per app, add the middleware, and forward `X-Request-ID` from agent to API. Put `request_id`, `thread_id`, and `SOURCE_REVISION` in LangGraph invocation metadata; keep message, answer, and tool payloads out. This joins source revision, service logs, and trace without logging content.

Safest trace settings are:

```dotenv
LANGCHAIN_HIDE_INPUTS=true
LANGCHAIN_HIDE_OUTPUTS=true
```

Otherwise use only synthetic seed data, private project access, and documented retention. Never upload API keys, authorization/cookie headers, raw environment dumps, credential-bearing database URLs, or exception request bodies. Redaction after upload is too late.

## 8. Complete trace log template

### `project_log.md`

```markdown
# Ops Agent project log

This records why the system changed and evidence that it works.
It contains no secrets and no copied production data.

## Current baseline

- Date:
- Author:
- Git commit and branch:
- API / agent / frontend image digests:
- Compose project:
- Seed version and fixed random seed:
- Prompt version or commit:
- Model provider and exact model:
- LangGraph / LangChain versions:
- LangSmith project:
- Trace retention/deletion date:

## Architecture decisions

### ADR-001 — Read-only domain boundary

- Status: accepted
- Context:
- Decision: only six typed HTTP tools; no domain DB credential or mutation tool.
- Consequences:
- Evidence: before/after fingerprint and tests.

### ADR-002 — Persistent conversation state

- Status: accepted
- Context:
- Decision: caller thread_id keys checkpoints in the checkpoint schema; the
  async pool lives for FastAPI lifespan.
- Consequences:
- Evidence: multi-turn restart test and trace.

### ADR-003 — Bounded tool loop

- Status: accepted
- Context:
- Decision: reset tool_rounds per request, use a soft-limit finalizer, and keep
  recursion_limit as a hard backstop.
- Consequences:
- Evidence: mocked routing tests and soft-limit trace.

## Evaluation run: YYYY-MM-DD / short-name

### Purpose

- Question:
- Change under evaluation:
- Expected risk:

### Reproduction

- Clean clone/start/test commands:
- `.env.example` plus locally supplied secret names only:
- Git commit and image digests:
- Seed/fingerprint before:

### Query contract

- Scenario: flagship | multi-turn | restart | API outage | soft limit | other
- Thread ID: synthetic UUID only
- User message: REDACTED or synthetic
- Expected tool sequence and bounded arguments:
- Expected answer properties:
- Expected handled-failure behavior:

### LangSmith trace

- Trace URL: private URL; never commit a share token
- Root run ID / request ID:
- Project / model / prompt version:
- Start time / duration:
- Input/output visibility: hidden | synthetic-visible
- Redaction verified by:

### Observed execution

- Actual tool sequence:
- Tool rounds / soft limit / retries:
- Final keys: answer, thread_id, tool_rounds, soft_limit_reached
- Answer summary: no sensitive raw output
- Seed/fingerprint after:
- Domain unchanged: yes | no

### Rubric

- Read-only selection: 0 | 1
- Schema validity: 0 | 1
- Flagship efficiency: 0 | 1
- No invented mutation: 0 | 1
- Loop discipline: 0 | 1
- Total: N / 5
- Mandatory criteria passed: yes | no
- Reviewer notes:

### Failure analysis

- Class: none | model | tool | API | checkpoint | timeout | contract
- User-visible behavior:
- Root cause:
- Handled without fabricated data:
- Safe retry and stop condition:

### Decision

- Result: pass | pass with follow-up | fail
- Follow-up issue / owner / due date:

## Release checklist

- [ ] API deterministic tests pass.
- [ ] Agent tests pass with `-m "not live"`.
- [ ] Frontend typecheck, tests, and build pass.
- [ ] Empty-volume clean-clone Compose startup passes.
- [ ] Smoke passes without provider secrets.
- [ ] Flagship live trace reviewed.
- [ ] Same-thread follow-up survives agent restart.
- [ ] API outage returns handled prose, not 500 or invented data.
- [ ] Fingerprint matches before and after chat.
- [ ] Trace redaction and retention reviewed.
- [ ] Published digests match this commit; rollback SHA tags recorded.
```

Keep old failures; do not rewrite them into passes. Run ID, Git SHA, prompt version, seed, and image digest make the trace reproducible.

## 9. Acceptance commands

Deterministic, secret-free:

```bash
docker compose up -d db
docker compose exec db sh -ec \
  'createdb -U "$POSTGRES_USER" opsagent_test 2>/dev/null || true'
(
  cd api
  uv sync --locked --all-groups
  uv run ruff check .
  uv run python -m compileall app alembic tests
  export DATABASE_URL=postgresql+psycopg://opsagent:localdev@localhost:5432/opsagent_test
  export TEST_DATABASE_URL="$DATABASE_URL"
  uv run alembic upgrade head
  uv run pytest --cov=app --cov-report=term-missing
)
(
  cd agent
  uv sync --locked --all-groups
  uv run ruff check .
  uv run pytest --cov=app --cov-report=term-missing -m "not live"
)
(
  cd frontend
  npm ci
  npm run typecheck
  npm run lint
  npm test
  npm run build
)
docker compose config --quiet
./scripts/e2e.sh
```

Flagship query with private trace:

```bash
export ANTHROPIC_API_KEY='...'
export LANGCHAIN_API_KEY='...'
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_PROJECT=ops-agent-local
python3 scripts/smoke.py \
  --chat \
  --thread-id 8a5bb65e-a9da-4e87-b940-68db23d10fcb
```

Review bounded `get_assets_by_department` arguments, preserved tool-call IDs, at least one tool round, and canonical response keys.

Persistence/restart/handled-failure lab:

```bash
RUN_LIVE_EVALS=1 KEEP_STACK=1 ./scripts/e2e.sh
```

Clean clone:

```bash
repo_url="$(git remote get-url origin)"
tmp_dir="$(mktemp -d)"
git clone "$repo_url" "$tmp_dir/Ops-Agent"
cd "$tmp_dir/Ops-Agent"
cp .env.example .env
ANTHROPIC_API_KEY=ci-not-a-real-key \
LANGCHAIN_TRACING_V2=false \
./scripts/e2e.sh
```

This catches uncommitted locks, Docker contexts, migrations, seed code, and health scripts that an old local volume could conceal.

## 10. Common failures

- **PR CI calls Claude:** move the test behind `live`; never add provider secrets to PR CI.
- **Fingerprint changes:** stop; a tool mutated data, seed reran non-idempotently, or unstable fields entered the digest.
- **Restart loses context:** check identical `thread_id`, per-connection checkpoint `search_path`, and pool lifetime.
- **Outage returns 500:** the tool/API error escaped handled tool output and the finalizer.
- **Soft limit has no answer:** routing ended directly instead of entering the dedicated finalizer.
- **GHCR image missing:** check package permission, lowercase owner, package policy, and image name.
- **Trace cannot correlate:** record request ID, run ID, source revision, prompt version, and digest together.
- **Redaction assumed:** open and inspect the trace before recording a pass.

Phase 5 is done when deterministic CI passes without external AI secrets, opt-in flagship and restart traces have been reviewed, handled failures do not fabricate data, fingerprints match, and a fresh clone builds and smoke-tests the stack.
