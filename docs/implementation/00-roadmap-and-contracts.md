# Ops Agent implementation roadmap and contracts

This is the contract-first index for building Ops Agent as a local, read-only portfolio project. Follow the guides in order and treat the contracts in this file as canonical. Later guides may explain an interface in more detail, but they must not rename fields, routes, tools, enum values, or environment variables defined here.

The intended learner workflow is:

1. Read the current phase and its definition of done.
2. Type the reference implementation from that phase's guide.
3. Run its focused tests before continuing.
4. Mark the checklist in this file.
5. Do not copy a later phase forward to make an earlier phase pass.

## Scope and non-goals

The finished project is a four-service local application:

- PostgreSQL stores business tables and enums in `public` and LangGraph checkpoint tables in `agent_checkpoints`.
- A FastAPI domain API owns all business-data access.
- A FastAPI/LangGraph agent calls six read-only HTTP-backed tools.
- A React/Vite frontend sends chat requests and displays final answers.

The project is deliberately read-only. It does not create, update, check out, check in, or retire assets through HTTP or chat. Seed scripts may write deterministic development data, and Alembic may change schema, but neither is an agent tool.

The following are future extensions, not foundation requirements:

- authentication and authorization;
- multi-tenant data isolation;
- write tools and human approval workflows;
- streaming chat responses;
- production pagination and rate limiting;
- remote infrastructure or public deployment;
- a vector database or retrieval-augmented generation.

The GitHub image workflow may publish container images to GHCR as a portfolio artifact. It must not imply that remote infrastructure has been provisioned.

## Actual state versus target state

### Actual repository state

The repository is an incomplete scaffold, not a working API:

- `.env.example`, `.gitignore`, `.vscode/settings.json`, and `docker-compose.yml` exist.
- `api/db.py` and `api/main.py` exist as untracked working-tree files.
- The tracked `api/app/routers/db.py` is deleted in the working tree.
- `api/main.py` contains ORM model declarations rather than a FastAPI application entry point.
- `api/main.py` imports `SQLEnum` but calls `SqlEnum`, which raises `NameError` while class bodies are evaluated.
- `api/db.py` contains misspellings, an unused/invalid `session` import, and a database URL default using `ops_agent`, while `.env.example` uses `opsagent`.
- The model draft has useful domain ideas—integer identifiers, closed enums, and checkout history as the holder source of truth—but it lacks migrations, constraints, schemas, services, routers, tests, and seed data.
- `docker-compose.yml` references `api`, `agent`, and `frontend` build contexts that do not yet contain Dockerfiles; two of those directories do not yet exist.
- Compose uses startup ordering only. It has no health checks or readiness conditions.
- There is no LangGraph agent, checkpoint persistence, chat endpoint, frontend, test suite, CI, or observability documentation.

Do not preserve a path merely because it appears in the partial scaffold. The target package layout below is the canonical destination. In particular, database setup belongs in `api/app/database.py`, ORM types belong in `api/app/models.py`, and the FastAPI application belongs in `api/app/main.py`.

### Target state

At completion:

- a fresh database can be migrated and seeded deterministically;
- all eight domain API routes return validated, deterministic JSON;
- the agent reaches domain data only through the domain API;
- all six tools are read-only and have narrow, enum-bounded schemas;
- LangGraph checkpoints survive agent restarts under the supplied `thread_id`;
- one chat turn may use several tools, but a soft tool-round limit always reaches a dedicated final-answer node;
- a hard recursion limit remains a last-resort safety net;
- the frontend creates and persists one UUID per browser tab before the first request and renders only user messages and final agent answers;
- Compose starts PostgreSQL, API, agent, and frontend with health-aware dependencies;
- pull-request tests are deterministic and do not require Anthropic or LangSmith credentials;
- real-model evaluation is opt-in and traceable.

## Canonical final tree

Generated lockfiles are committed after running the package managers; guides must not invent their contents.

```text
Ops-Agent/
├── .env.example
├── .gitignore
├── README.md
├── docker-compose.yml
├── project_log.md
├── api/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── alembic.ini
│   ├── pyproject.toml
│   ├── uv.lock                         # generated
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── seed.py
│   │   ├── services.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── assets.py
│   │   │   ├── checkouts.py
│   │   │   ├── health.py
│   │   │   └── users.py
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 0001_initial.py
│   └── tests/
│       ├── conftest.py
│       ├── test_assets.py
│       ├── test_checkouts.py
│       ├── test_constraints.py
│       ├── test_health.py
│       ├── test_seed.py
│       └── test_users.py
├── agent/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── uv.lock                         # generated
│   ├── app/
│   │   ├── __init__.py
│   │   ├── api_client.py
│   │   ├── config.py
│   │   ├── graph.py
│   │   ├── main.py
│   │   ├── nodes.py
│   │   ├── prompts.py
│   │   ├── routing.py
│   │   ├── schemas.py
│   │   ├── state.py
│   │   └── tools.py
│   └── tests/
│       ├── conftest.py
│       ├── test_api_client.py
│       ├── test_chat.py
│       ├── test_graph.py
│       └── test_tools.py
├── frontend/
│   ├── Dockerfile
│   ├── index.html
│   ├── nginx.conf
│   ├── package.json
│   ├── package-lock.json               # generated
│   ├── tsconfig.json
│   ├── tsconfig.app.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.css
│       ├── App.test.tsx
│       ├── App.tsx
│       ├── main.tsx
│       ├── test-setup.ts
│       ├── vite-env.d.ts
│       ├── api/
│       │   ├── chat.test.ts
│       │   └── chat.ts
│       ├── components/
│       │   ├── ChatComposer.tsx
│       │   ├── ChatMessage.tsx
│       │   └── ChatTranscript.tsx
│       └── lib/
│           └── thread.ts
├── scripts/
│   ├── reset-local-db.sh
│   └── smoke-test.sh
├── tests/
│   └── e2e/
│       └── chat.spec.ts
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
└── docs/
    └── implementation/
        ├── 00-roadmap-and-contracts.md
        ├── 01-domain-api.md
        ├── 02-langgraph-agent.md
        ├── 03-react-frontend.md
        ├── 04-compose-and-configuration.md
        └── 05-testing-ci-and-observability.md
```

The root `tests/e2e` suite tests the assembled product. Unit and integration tests stay beside the service they exercise.

## Architecture and data flow

### Service boundaries

**PostgreSQL**

- The `public` schema contains business tables and enum types.
- The `agent_checkpoints` schema contains LangGraph checkpoint tables.
- The API accesses business data in `public`.
- The agent checkpointer uses `agent_checkpoints`; the agent reaches business data only through HTTP.
- Sharing one local PostgreSQL instance reduces setup cost; separate schemas preserve ownership boundaries.

**Domain API**

- Owns SQLAlchemy models, transactions, migrations, seed data, query construction, and validated business-data JSON.
- Exposes exactly the eight GET routes defined below.
- Returns deterministic ordering so tests and model observations are stable.
- Never imports LangGraph or an LLM SDK.

**Agent**

- Owns prompt policy, the six tool definitions, graph state, tool-loop routing, checkpoint persistence, and `POST /chat`.
- Uses an async HTTP client to call the domain API.
- Does not import API ORM models and does not query business tables.
- Holds one `AsyncPostgresSaver` for the FastAPI lifespan rather than opening a checkpointer per request.

**Frontend**

- Calls only the agent's `/chat` endpoint.
- Creates a UUID once per tab, stores it in `sessionStorage`, and sends it on every request.
- Shows user text, loading/error status, and final `answer`; internal tool calls are trace/debug data, not chat messages.

### End-to-end request flow

1. The browser reads its tab-local `thread_id`; if absent, it creates a UUID and stores it before sending.
2. The frontend sends `{message, thread_id}` to `POST /chat`.
3. The agent requires and validates the non-null UUID.
4. The graph invocation uses that UUID as LangGraph's `configurable.thread_id`.
5. `AsyncPostgresSaver` loads prior messages from the `agent_checkpoints` schema.
6. The model node receives prior messages, the current user message, the system prompt, and six tool schemas.
7. If the model emits tool calls, `ToolNode` executes them; the model is only re-entered while another round remains available.
8. Each tool validates arguments and makes an async GET request to the domain API.
9. The domain router validates query/path values, a service builds the SQLAlchemy query, and PostgreSQL reads business tables in `public`.
10. The tool client validates the `{data,error,meta}` envelope and passes `data` back as tool output. Tool-call IDs remain unchanged so each `ToolMessage` matches its originating call.
11. After all calls in that assistant message complete, the tools node records one completed tool round. One assistant message containing one or more tool calls is one round.
12. A normal text response ends the graph. After `MAX_TOOL_ROUNDS` completed rounds, routing goes from tools to a dedicated finalizer model node with tools disabled.
13. The checkpoint is saved, and the agent returns the exact chat response envelope.
14. The frontend saves the returned `thread_id` and renders `answer`.

### Why HTTP is the agent boundary

The agent could technically query PostgreSQL directly, but that would duplicate business query rules, couple graph code to business storage, and make tool tests harder to isolate. HTTP keeps one business-data owner, gives the tools realistic failure modes, and makes the API independently demonstrable in a portfolio.

## Domain model invariants

Canonical enums are case-sensitive JSON strings:

- `AssetCategory`: `laptop`, `monitor`, `phone`, `desktop`, `tablet`
- `AssetStatus`: `available`, `checked_out`, `retired`
- `Region`: `us-east`, `us-west`, `emea`, `apac`
- `Department`: `Engineering`, `Marketing`, `Sales`, `Finance`, `IT`, `HR`, `Operations`

Domain rules:

- Integer primary keys are intentional: they are compact in tool calls and easy to inspect in traces.
- Asset tags and user emails are unique.
- Checkout history is the source of truth for holder identity.
- An open checkout has `checked_in_at = null`.
- A partial unique index permits at most one open checkout per asset.
- A check constraint requires `checked_in_at >= checked_out_at` when check-in exists.
- A consistent open checkout implies `asset.status == "checked_out"`. Seed and service tests enforce this cross-row rule.
- Department is a property of a user, not an asset. “Assets by department” means assets currently held by users in that department.
- All persisted and serialized timestamps are timezone-aware UTC values.
- Alembic owns schema creation. Application startup must not call `Base.metadata.create_all()`.

## Shared response shapes

Every domain API response uses the Phase 1 envelope:

```json
{
  "data": [],
  "error": null,
  "meta": {
    "count": 0,
    "limit": 50
  }
}
```

On success, `data` contains the typed payload and `error` is null. `meta.count` is the number of returned items, or `1` for a successful item/health response; `meta.limit` is the applied collection limit when that route accepts one and otherwise null. On failure, `data` is null and `error` contains stable `code` and human-readable `message` fields.

The following examples define payloads placed inside `data`; they are not complete HTTP responses.

`AssetRead`:

```json
{
  "id": 101,
  "tag": "LAP-0101",
  "category": "laptop",
  "model": "ThinkPad T14",
  "status": "checked_out",
  "region": "emea",
  "last_synced_at": "2026-07-01T14:30:00Z",
  "current_holder": {
    "id": 42,
    "name": "Avery Chen",
    "email": "avery.chen@example.test",
    "department": "IT"
  }
}
```

`current_holder` is null for an asset without an open checkout.

`UserRead`:

```json
{
  "id": 42,
  "name": "Avery Chen",
  "email": "avery.chen@example.test",
  "department": "IT"
}
```

`CheckoutRead` embeds both sides so tools never need an N+1 sequence of lookups:

```json
{
  "id": 9001,
  "checked_out_at": "2026-06-15T09:00:00Z",
  "checked_in_at": null,
  "asset": {
    "id": 101,
    "tag": "LAP-0101",
    "category": "laptop",
    "model": "ThinkPad T14",
    "status": "checked_out",
    "region": "emea"
  },
  "user": {
    "id": 42,
    "name": "Avery Chen",
    "email": "avery.chen@example.test",
    "department": "IT"
  }
}
```

## Exact domain API contract

The domain API listens on port `8000`. All paths are relative to its base URL. Successful collection endpoints place `[]` in envelope `data` when no rows match. Item endpoints return `404` only when the addressed parent resource does not exist. Successes and handled errors—including validation and not-found responses—retain the `{data,error,meta}` shape.

Collection ordering is part of the contract:

- asset collections: ascending `asset.id`;
- user collections: ascending `user.name`, then `user.id`;
- checkout history: descending `checked_out_at`, then descending `checkout.id`.

Static `/assets/search`, `/assets/stale`, and `/assets/by-department` routes must be registered before `/assets/{asset_id}` so FastAPI never tries to parse a static path segment as an integer ID.

### `GET /health`

Purpose: readiness for Compose and smoke tests.

Parameters: none.

Success `200` after a successful `SELECT 1`:

```json
{
  "data": {"status": "ok", "database": "ok"},
  "error": null,
  "meta": {"count": 1, "limit": null}
}
```

If the database cannot be reached, return `503`:

```json
{
  "data": null,
  "error": {"code": "service_unavailable", "message": "database unavailable"},
  "meta": {"count": 0, "limit": null}
}
```

### `GET /assets/search`

Purpose: bounded asset discovery using optional enum filters. It does not accept or require a free-text query.

Query parameters:

- `category`: optional `AssetCategory`;
- `status`: optional `AssetStatus`;
- `region`: optional `Region`;
- `limit`: optional integer, default `50`, range `1..100`.

Success: `200` with `ApiResponse[AssetRead[]]`; `meta.limit` equals the applied limit.

Example:

```http
GET /assets/search?category=laptop&region=emea&limit=25
```

### `GET /assets/stale`

Purpose: list assets whose last synchronization is at or before a computed UTC cutoff.

Query parameters:

- `stale_days`: required integer, range `1..3650`;
- `category`: optional `AssetCategory`;
- `status`: optional `AssetStatus`;
- `region`: optional `Region`.

The predicate is `last_synced_at <= request_time_utc - stale_days`. Compute one request-scoped UTC cutoff and pass it into the service; do not use database-local time in one layer and application-local time in another.

Success: `200` with `ApiResponse[AssetRead[]]`.

### `GET /assets/by-department`

Purpose: answer the flagship bounded query in one API call by joining assets to open checkouts and their users.

Query parameters:

- `department`: required `Department`;
- `category`: optional `AssetCategory`;
- `status`: optional `AssetStatus`;
- `region`: optional `Region`;
- `stale_days`: optional integer, range `1..3650`.

Only open checkouts participate. The result therefore represents assets currently held by users in the requested department. `stale_days`, when present, uses the same inclusive cutoff rule as `/assets/stale`.

Success: `200` with `ApiResponse[AssetRead[]]`.

Example:

```http
GET /assets/by-department?department=IT&category=laptop&region=emea&stale_days=30
```

This endpoint deliberately accepts category, status, region, and staleness together. Fetching all department assets and asking the LLM to filter them would waste tokens, make answers less reliable, and move deterministic query logic into probabilistic model behavior.

### `GET /assets/{asset_id}`

Purpose: retrieve one asset and its current holder, if any.

Path parameter:

- `asset_id`: required positive integer.

Success: `200` with `ApiResponse[AssetRead]`.

Failure: `404` with `data: null`, error code `not_found`, message `asset not found`, and zero-count metadata.

### `GET /checkouts/asset/{asset_id}`

Purpose: retrieve complete checkout history for one asset.

Path parameter:

- `asset_id`: required positive integer.

Success: `200` with `ApiResponse[CheckoutRead[]]`, including an empty `data` array for a known asset with no checkout history.

Failure: `404` with envelope error code `not_found` and message `asset not found`.

### `GET /checkouts/user/{user_id}`

Purpose: retrieve the assets currently held by one user.

Path parameter:

- `user_id`: required positive integer.

Success: `200` with `ApiResponse[AssetRead[]]`, including an empty `data` array for a known user with no current assets.

Failure: `404` with envelope error code `not_found` and message `user not found`.

### `GET /users/search`

Purpose: search users within one department.

Query parameters:

- `department`: required `Department`;
- `q`: optional trimmed name-or-email substring, length `1..100` when supplied.

Success: `200` with `ApiResponse[UserRead[]]`.

Example:

```http
GET /users/search?department=IT&q=avery
```

Department is required because the corresponding tool is specifically a department search; this prevents an accidental unbounded people-directory query.

## Exact chat contract

The agent API listens on port `8001`.

### `POST /chat`

Request body has exactly two keys:

```json
{
  "message": "Which IT laptops in EMEA have not synced in 30 days?",
  "thread_id": "1af23fc2-26de-4f31-b7ac-e8f40ea82122"
}
```

Request rules:

- `message` is required, trimmed, non-empty, and at most 4,000 characters;
- `thread_id` is required, non-null, and must be a UUID string;
- the frontend creates this UUID once per tab before its first request;
- unknown extra fields are rejected.

Success `200` has exactly four keys:

```json
{
  "answer": "Two IT laptops in EMEA have not synced in 30 days: LAP-0101 and LAP-0134.",
  "thread_id": "1af23fc2-26de-4f31-b7ac-e8f40ea82122",
  "tool_rounds": 1,
  "soft_limit_reached": false
}
```

Response rules:

- `answer` is a non-empty final natural-language answer;
- `thread_id` is the same UUID supplied in the request;
- `tool_rounds` is a non-negative integer counting completed tools-node rounds during this request only;
- `soft_limit_reached` is `true` only when routing used the dedicated soft-limit finalizer;
- per-request counters are reset for every HTTP request and are not restored from checkpoints;
- unknown response fields are not part of the public contract.

A handled upstream failure should still produce `200` when the graph can explain the problem honestly. Invalid chat input returns `422`. An unexpected graph/checkpointer failure returns `503` with a generic `detail`; stack traces and secrets never enter the response.

## Six canonical tool contracts

Tool schemas are strict: reject unknown arguments, use the canonical enums, and include descriptions that tell the model when not to use a tool. Tools perform no writes. They return JSON-compatible objects from the API; they do not compose the final prose answer.

All tool wrappers share these behaviors:

- use the lifespan-owned async API client;
- apply the configured timeout;
- retry only transport failures and `502`/`503`/`504`, never validation or not-found responses;
- validate the API's `{data,error,meta}` envelope and return its successful `data` payload;
- normalize a successful empty collection payload to `[]`;
- preserve payload fields and UTC timestamp strings;
- turn expected failures into a concise JSON error payload for the `ToolMessage`;
- never fabricate an empty success after an upstream error.

Canonical tool error payload:

```json
{
  "error": {
    "kind": "not_found",
    "message": "asset 999 was not found"
  }
}
```

Allowed `kind` values are `invalid_request`, `not_found`, `upstream_unavailable`, and `unexpected_response`.

### `search_assets`

Use for bounded asset discovery by category, status, and/or region.

Arguments:

```json
{
  "category": "laptop",
  "status": "checked_out",
  "region": "emea",
  "limit": 25
}
```

- `category`, `status`, `region`: optional canonical enums;
- `limit`: optional integer, default `50`, range `1..100`.

HTTP mapping: `GET /assets/search`.

Returns: `AssetRead[]`.

### `find_stale_assets`

Use for stale synchronization questions that are not constrained by holder department.

Arguments:

```json
{
  "stale_days": 30,
  "category": "laptop",
  "status": "checked_out",
  "region": "emea"
}
```

- `stale_days`: required integer, range `1..3650`;
- `category`, `status`, `region`: optional canonical enums.

HTTP mapping: `GET /assets/stale`.

Returns: `AssetRead[]`.

### `get_assets_by_department`

Use for assets currently held by members of one department. Prefer this single tool over broad retrieval plus model-side filtering.

Arguments:

```json
{
  "department": "IT",
  "category": "laptop",
  "status": "checked_out",
  "region": "emea",
  "stale_days": 30
}
```

- `department`: required canonical `Department`;
- `category`, `status`, `region`: optional canonical enums;
- `stale_days`: optional integer, range `1..3650`.

HTTP mapping: `GET /assets/by-department`.

Returns: `AssetRead[]`.

### `get_checkout_history`

Use when the user asks who had an asset, when it was checked out, or for its historical custody.

Arguments:

```json
{"asset_id": 101}
```

- `asset_id`: required positive integer.

HTTP mapping: `GET /checkouts/asset/{asset_id}`.

Returns: `CheckoutRead[]`.

### `get_user_assets`

Use when the user asks which assets a known user currently holds.

Arguments:

```json
{"user_id": 42}
```

- `user_id`: required positive integer.

HTTP mapping: `GET /checkouts/user/{user_id}`.

Returns: the `AssetRead[]` payload supplied directly by the endpoint. A known user with no current assets returns `[]`.

### `search_users_by_department`

Use to resolve a user in a known department before calling `get_user_assets`.

Arguments:

```json
{
  "department": "IT",
  "query": "avery"
}
```

- `department`: required canonical `Department`;
- `query`: optional string, length `1..100`.

HTTP mapping: `GET /users/search`, with `query` renamed to `q`.

Returns: `UserRead[]`.

The model should ask for clarification when multiple users plausibly match. It must not guess a `user_id`.

## Graph loop and termination contract

The normal graph is:

```text
START -> model
model -- no tool calls -------------------------------> END
model -- tool calls --------------------> tools
tools -- completed rounds < MAX_TOOL_ROUNDS ----------> model
tools -- completed rounds = MAX_TOOL_ROUNDS ----------> finalizer -> END
```

The state extends LangGraph `MessagesState` with request-local `tool_rounds` and `soft_limit_reached`.

Routing rules:

1. A plain assistant message ends normally.
2. A model message with one or more tool calls always routes to `ToolNode` while another completed round is permitted.
3. `ToolNode` executes every call in that assistant message, producing matching `ToolMessage` records.
4. After `ToolNode` completes the batch, increment `tool_rounds` once, including when a tool returns a handled error result.
5. If `tool_rounds < MAX_TOOL_ROUNDS`, route back to the model. If it equals `MAX_TOOL_ROUNDS`, route from tools to `finalizer`.
6. The finalizer therefore receives matched tool results and never sees an unresolved assistant tool call. It binds no tools, answers from evidence already gathered, states uncertainty, and mentions that further lookup was stopped.
7. The finalizer's assistant message is the only graph output used as `answer`.
8. `RECURSION_LIMIT` remains higher than the soft path's node count and handles programming errors or unexpected graph cycles. It is not the user experience for ordinary loop exhaustion.

The dedicated finalizer is required. Routing to it only after tools complete both honors the full `MAX_TOOL_ROUNDS` budget and avoids an unmatched tool call.

## Environment-variable matrix

Keep safe defaults in `.env.example`; keep real secrets only in ignored `.env` or the shell. The Compose environment uses service names such as `db` and `api`. A process run directly on the host must override those hosts with `localhost`.

### PostgreSQL and domain API

- `POSTGRES_USER`
  - Owner: PostgreSQL container.
  - Required for Compose.
  - Example: `opsagent`.
- `POSTGRES_PASSWORD`
  - Owner: PostgreSQL container and connection URLs.
  - Required; secret.
  - Example placeholder: `change-me`.
- `POSTGRES_DB`
  - Owner: PostgreSQL container.
  - Required for Compose.
  - Example: `opsagent`.
- `DATABASE_URL`
  - Owner: domain API, Alembic, and seed command.
  - Required.
  - Compose example: `postgresql+psycopg://opsagent:change-me@db:5432/opsagent`.
  - Host example: `postgresql+psycopg://opsagent:change-me@localhost:5432/opsagent`.
- `CORS_ORIGINS`
  - Owner: agent API; comma-separated exact browser origins.
  - Local default: `http://localhost:5173`.

### Agent and checkpointer

- `CHECKPOINT_DATABASE_URL`
  - Owner: agent `AsyncPostgresSaver`.
  - Required.
  - Compose example: `postgresql://opsagent:change-me@db:5432/opsagent`.
  - Host example: `postgresql://opsagent:change-me@localhost:5432/opsagent`.
  - Every pooled connection must use `search_path=agent_checkpoints,public`; setting it only during initial setup is insufficient.
- `CHECKPOINT_SCHEMA`
  - Owner: agent checkpointer setup.
  - Required canonical value: `agent_checkpoints`.
- `API_BASE_URL`
  - Owner: agent HTTP client.
  - Compose default: `http://api:8000`.
  - Host default: `http://localhost:8000`.
- `API_TIMEOUT_SECONDS`
  - Owner: agent HTTP client.
  - Default: `5`.
- `API_MAX_RETRIES`
  - Owner: agent HTTP client.
  - Default: `2`.
- `ANTHROPIC_API_KEY`
  - Owner: model client.
  - Required only for real chat/evaluation; secret.
- `ANTHROPIC_MODEL`
  - Owner: model client.
  - Pin an explicit supported model in `.env.example`; do not rely on an SDK-changing default.
- `MAX_TOOL_ROUNDS`
  - Owner: graph routing.
  - Default: `4`.
- `RECURSION_LIMIT`
  - Owner: graph invocation.
  - Default: `25`; must remain above the soft path's maximum node count.

### Frontend

- `VITE_AGENT_URL`
  - Owner: Vite build and typed frontend client.
  - Local browser value: `http://localhost:8001`.
  - This is browser-visible and build-time, even when the frontend is built in Docker. Never set it to `http://agent:8001`, which a host browser cannot resolve.

### Observability

- `LANGCHAIN_TRACING_V2`
  - Owner: LangSmith integration.
  - Default for ordinary local/CI tests: `false`.
  - Set `true` only for an intentional traced run.
- `LANGCHAIN_API_KEY`
  - Owner: LangSmith integration.
  - Optional secret; never required by pull-request CI.
- `LANGCHAIN_PROJECT`
  - Owner: LangSmith integration.
  - Default: `ops-agent`.
- `LOG_LEVEL`
  - Owner: API and agent structured logging.
  - Default: `INFO`.

The current `ops_agent` versus `opsagent` URL drift must be removed. One credential/database naming convention must be used in `.env.example`, Compose, application settings, Alembic, tests, and all commands.

## Implementation order

Dependencies make this sequence deliberate. Do not start the agent against an undocumented or changing API.

### Phase 0 — Contracts and learning map

Guide: this file.

Tasks:

- freeze service boundaries, enums, routes, JSON, tools, chat behavior, and environment names;
- record actual-state gaps without claiming the scaffold works;
- create the phase checklist and acceptance criteria.

Definition of done:

- all later phases can cite one canonical contract;
- eight domain routes, six tools, and four chat response fields are explicit;
- current mismatches and both required architecture corrections are documented.

### Phase 1 — Domain API and deterministic data

Guide: `01-domain-api.md`.

Tasks:

- create settings, database lifecycle, ORM models, Pydantic schemas, services, routers, and FastAPI assembly;
- create Alembic configuration and the initial migration for business tables and enums in `public`;
- enforce one open checkout per asset and valid timestamp ordering in PostgreSQL;
- create deterministic Faker seed data containing flagship-query fixtures;
- add focused API and seed tests;
- add the API manifest and Dockerfile.

Definition of done:

- a clean database migrates to head and seeds twice without duplicate growth;
- all eight routes match this contract;
- unknown resources, empty collections, invalid enums, stale cutoffs, and deterministic ordering are tested;
- the flagship department/category/region/staleness query is answered by one bounded SQL query;
- no runtime `create_all()` is used.

### Phase 2 — Persistent LangGraph agent

Guide: `02-langgraph-agent.md`.

Tasks:

- create validated settings and chat schemas;
- create one lifespan-owned async API client and checkpointer;
- implement the six strict tools;
- build model, tool, finalizer, routing, and graph modules;
- expose canonical `POST /chat`;
- test with a fake model and mocked HTTP transport.

Definition of done:

- every tool maps exactly to its canonical API route and shape;
- tool-call IDs survive model-to-tool execution;
- empty, not-found, validation, timeout, retryable, and malformed-response cases are deterministic;
- a supplied thread resumes after an agent restart;
- request-local counters reset between turns;
- up to `MAX_TOOL_ROUNDS` complete successfully before the tools node routes to the no-tools finalizer;
- tests need neither Anthropic nor LangSmith secrets.

### Phase 3 — React chat frontend

Guide: `03-react-frontend.md`.

Tasks:

- create Vite/React/TypeScript configuration;
- create runtime-validated chat request/response handling;
- create tab-local thread storage and accessible chat components;
- implement loading, handled error, keyboard, IME, and responsive states;
- add component and client tests;
- add Nginx and the production frontend Dockerfile.

Definition of done:

- the client sends exactly `{message, thread_id}` and reads `answer`;
- the frontend creates and stores a thread UUID before its first request;
- every request carries that non-null UUID, and a new tab creates a separate one;
- users cannot double-submit while a request is pending;
- Enter, Shift+Enter, and composition events behave correctly;
- only user messages and final answers are visible;
- type-check, tests, and production build pass.

### Phase 4 — Compose and configuration

Guide: `04-compose-and-configuration.md`.

Tasks:

- reconcile the root environment contract;
- add health checks and health-aware dependencies;
- define migration, seed, and normal startup ownership;
- add useful reset and smoke scripts;
- bind local ports intentionally and preserve the database volume.

Definition of done:

- a clean four-service startup works from the documented commands;
- the API waits for PostgreSQL readiness and the agent waits for API readiness;
- business tables/enums are in `public` and checkpoint tables are in `agent_checkpoints`;
- browser and container URLs are correct;
- reset/recovery is explicit and safe;
- no secret is committed.

### Phase 5 — Testing, CI, observability, and packaging

Guide: `05-testing-ci-and-observability.md`.

Tasks:

- add the assembled-product smoke/E2E path;
- create path-aware CI jobs for API, agent, frontend, and container builds;
- create GHCR image publishing without claiming remote deployment;
- add structured logging and the LangSmith trace-review template;
- separate deterministic tests from opt-in real-model evaluation.

Definition of done:

- pull-request CI passes without external AI credentials;
- changed paths trigger the correct jobs;
- logs correlate request, thread, and trace IDs without logging secrets or full sensitive payloads;
- an opt-in trace demonstrates the flagship query and is scored against a documented rubric;
- image tags are immutable and source-correlated;
- the read-only business-data fingerprint is unchanged by chat/E2E tests.

### Phase 6 — Clean-clone acceptance

This is a verification pass, not another implementation guide.

Definition of done:

- a learner can clone, configure, migrate, seed, start, test, and use the project using repository documentation alone;
- the flagship query returns only matching IT laptops in EMEA at least 30 days stale;
- a follow-up question demonstrates checkpointed context;
- a forced API outage produces an honest handled answer;
- the soft-limit fixture produces final prose with `soft_limit_reached: true`;
- restarting the agent preserves a supplied thread;
- all file paths, imports, dependencies, routes, fields, and commands agree across guides.

## Complete implementation checklist

### Contract and documentation

- [ ] `docs/implementation/00-roadmap-and-contracts.md` is complete and canonical.
- [ ] `docs/implementation/01-domain-api.md` contains every Phase 1 file.
- [ ] `docs/implementation/02-langgraph-agent.md` contains every Phase 2 file.
- [ ] `docs/implementation/03-react-frontend.md` contains every Phase 3 file.
- [ ] `docs/implementation/04-compose-and-configuration.md` contains every Phase 4 file.
- [ ] `docs/implementation/05-testing-ci-and-observability.md` contains every Phase 5 file.
- [ ] `README.md` provides the short happy path and links to the guides.
- [ ] `project_log.md` records architecture decisions and trace/evaluation evidence.

### Domain API

- [ ] `api/.dockerignore`
- [ ] `api/app/__init__.py`
- [ ] `api/app/config.py`
- [ ] `api/app/database.py`
- [ ] `api/app/models.py`
- [ ] `api/app/schemas.py`
- [ ] `api/app/services.py`
- [ ] `api/app/routers/__init__.py`
- [ ] `api/app/routers/assets.py`
- [ ] `api/app/routers/checkouts.py`
- [ ] `api/app/routers/health.py`
- [ ] `api/app/routers/users.py`
- [ ] `api/app/main.py`
- [ ] `api/app/seed.py`
- [ ] `api/alembic.ini`
- [ ] `api/alembic/env.py`
- [ ] `api/alembic/script.py.mako`
- [ ] `api/alembic/versions/0001_initial.py`
- [ ] `api/tests/conftest.py`
- [ ] `api/tests/test_assets.py`
- [ ] `api/tests/test_checkouts.py`
- [ ] `api/tests/test_health.py`
- [ ] `api/tests/test_constraints.py`
- [ ] `api/tests/test_seed.py`
- [ ] `api/tests/test_users.py`
- [ ] `api/pyproject.toml`
- [ ] generated `api/uv.lock`
- [ ] `api/Dockerfile`

### LangGraph agent

- [ ] `agent/app/__init__.py`
- [ ] `agent/app/config.py`
- [ ] `agent/app/schemas.py`
- [ ] `agent/app/state.py`
- [ ] `agent/app/prompts.py`
- [ ] `agent/app/api_client.py`
- [ ] `agent/app/tools.py`
- [ ] `agent/app/nodes.py`
- [ ] `agent/app/routing.py`
- [ ] `agent/app/graph.py`
- [ ] `agent/app/main.py`
- [ ] `agent/tests/conftest.py`
- [ ] `agent/tests/test_api_client.py`
- [ ] `agent/tests/test_tools.py`
- [ ] `agent/tests/test_graph.py`
- [ ] `agent/tests/test_chat.py`
- [ ] `agent/pyproject.toml`
- [ ] generated `agent/uv.lock`
- [ ] `agent/Dockerfile`

### Frontend

- [ ] `frontend/index.html`
- [ ] `frontend/package.json`
- [ ] generated `frontend/package-lock.json`
- [ ] `frontend/tsconfig.json`
- [ ] `frontend/tsconfig.app.json`
- [ ] `frontend/vite.config.ts`
- [ ] `frontend/src/vite-env.d.ts`
- [ ] `frontend/src/main.tsx`
- [ ] `frontend/src/App.tsx`
- [ ] `frontend/src/App.css`
- [ ] `frontend/src/api/chat.ts`
- [ ] `frontend/src/api/chat.test.ts`
- [ ] `frontend/src/lib/thread.ts`
- [ ] `frontend/src/components/ChatComposer.tsx`
- [ ] `frontend/src/components/ChatMessage.tsx`
- [ ] `frontend/src/components/ChatTranscript.tsx`
- [ ] `frontend/src/test-setup.ts`
- [ ] `frontend/src/App.test.tsx`
- [ ] `frontend/nginx.conf`
- [ ] `frontend/Dockerfile`

### Operations and quality

- [ ] Root `.env.example` matches the environment matrix.
- [ ] Root `.gitignore` excludes local secrets, caches, build output, and test artifacts.
- [ ] `docker-compose.yml` has health checks and persistent storage.
- [ ] `scripts/reset-local-db.sh` requires explicit confirmation before deleting data.
- [ ] `scripts/smoke-test.sh` verifies all service boundaries.
- [ ] `tests/e2e/chat.spec.ts` exercises the assembled UI.
- [ ] `.github/workflows/ci.yml` is path-aware and credential-free for pull requests.
- [ ] `.github/workflows/deploy.yml` publishes source-correlated GHCR images only.
- [ ] API and agent emit structured, redacted logs.
- [ ] LangSmith real-model evaluation is opt-in.
- [ ] Clean-clone acceptance passes.

## Key corrections that must survive implementation

### Bound deterministic filters in the API and tool schema

The flagship question combines department, category, region, and staleness. `get_assets_by_department` must accept all four dimensions and map them to one API query. Do not retrieve every departmental asset and ask the model to filter JSON. The database is faster and exact; the model is neither.

### Use a dedicated soft-loop finalizer

The soft limit is not an exception and not a hard stop. Execute up to `MAX_TOOL_ROUNDS` complete tool rounds, then route from tools to a model node with no tools bound and require a useful answer from evidence already gathered. This preserves matching tool results. Keep a larger `RECURSION_LIMIT` only as defensive containment.

### Correct the enum alias

The partial model imports `Enum as SQLEnum` and then calls `SqlEnum`. Python names are case-sensitive. Use one alias consistently, preferably `SQLEnum`, in the canonical model file.

### Eliminate database URL drift

`ops_agent:ops_agent/ops_agent` and `opsagent:change-me/opsagent` describe different credentials and databases. Pick the environment matrix's `opsagent` convention and use it everywhere. Also use explicit SQLAlchemy driver URLs where SQLAlchemy consumes the value.

### Keep migration ownership singular

Alembic creates and changes business tables and enums in `public`. The API must not call `create_all()` at startup, and seed code must not silently create missing tables. A missing migration should fail visibly.

### Keep checkpointer scope and schema correct

Create one `AsyncPostgresSaver` in FastAPI lifespan, call its setup in controlled startup, and close it on shutdown. Ensure every pooled connection has the checkpoint `search_path`; a one-time `SET search_path` on one connection does not configure the pool.

### Keep async boundaries async

Agent route, graph invocation, tool functions, HTTP client, and checkpointer are async end-to-end. Calling synchronous HTTP or database functions inside graph nodes blocks the event loop and undermines concurrency.

### Preserve tool-call identity

Use current `MessagesState` and `ToolNode` behavior. Do not rebuild assistant/tool messages in a way that drops `tool_call_id`; providers require each result to match a call.

### Separate deterministic CI from model evaluation

Fake the model and mock HTTP for CI. A real Anthropic call is an opt-in evaluation, not a unit test. LangSmith tracing must also be optional so forks and pull requests work without secrets.

## Common pitfalls

- Treating the current `api/main.py` as an app entry point even though it contains models.
- Keeping duplicate database modules at both `api/db.py` and `api/app/routers/db.py`.
- Importing application modules as top-level `database` or `models` instead of package-qualified `app.database` and `app.models`.
- Defining `/assets/{asset_id}` before static asset routes and receiving a `422` for `/assets/stale`.
- Returning `404` for an empty search. Empty collections are valid `200` responses.
- Returning `[]` when an addressed asset or user does not exist. Parent existence is a separate `404` case.
- Using naive datetimes or comparing local time with UTC timestamps.
- Making staleness exclusive in one endpoint and inclusive in another.
- Storing `checked_out_to` on `assets` and creating a second holder source of truth.
- Relying only on application checks for one open checkout; concurrent writes require a database partial unique index.
- Letting `checked_in_at` precede `checked_out_at`.
- Giving the agent direct access to business tables in `public`.
- Exposing broad tools with free-text department/category/status values.
- Letting the LLM guess a user when a department search returns several matches.
- Counting each parallel tool call as a separate round. One assistant tool-call message is one round.
- Persisting `tool_rounds` in thread history and accidentally carrying a previous request's budget forward.
- Routing to the finalizer before the last permitted tool calls have produced matching `ToolMessage` results.
- Using the hard LangGraph recursion exception as normal loop control.
- Returning the last raw `AIMessage` object instead of a validated `answer` string.
- Changing `answer` to `response`, `content`, or `message` in one layer.
- Generating a new thread ID on every turn, waiting for the server to create one, or storing it in shared `localStorage`; create one UUID per tab in `sessionStorage`.
- Displaying internal tool messages in the end-user transcript.
- Using Docker service hostnames in browser JavaScript.
- Assuming `depends_on` means a dependency is ready; use health checks and readiness conditions.
- Requiring Anthropic or LangSmith keys to run pull-request tests.
- Pasting fabricated lockfiles into a guide instead of generating them with the package manager.
- Logging API keys, full prompts, emails, or raw tool payloads without redaction.
- Calling an image-publishing workflow a deployed production system.
- Adding write endpoints or tools “for completeness” and violating the read-only scope.

## Final acceptance queries

Use deterministic seed fixtures so these checks have stable expected evidence:

1. “Which IT laptops in EMEA have not synced in 30 days?”
   - Expected tool: one `get_assets_by_department` call with all bounded filters.
2. “Who currently has asset 101?”
   - Expected tool: `get_checkout_history` with `asset_id: 101`, then select the open history row.
3. “What else do they currently have?”
   - Expected behavior: resolve the prior user's ID from checkpointed context, then call `get_user_assets`.
4. “Find Avery in IT.”
   - Expected tool: `search_users_by_department`.
5. A fixture model that continues requesting tools after `MAX_TOOL_ROUNDS`.
   - Expected response: all allowed rounds completed with matched tool results, then final prose with `tool_rounds` equal to `MAX_TOOL_ROUNDS` and `soft_limit_reached: true`.
6. Stop the domain API and ask an asset question.
   - Expected behavior: bounded retries followed by an honest handled answer, not invented inventory.

The second acceptance query exposes an intentional economy in the six-tool set: there is no seventh `get_asset` tool, and `search_assets` intentionally has no text query. Tool-driven checkout history therefore starts from a known integer asset ID. The API still exposes `GET /assets/{asset_id}` for direct API consumers and future tool evolution.
