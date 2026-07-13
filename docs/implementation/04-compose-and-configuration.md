# Compose and configuration

This phase connects the API, agent, frontend, and PostgreSQL into one local portfolio stack. It intentionally uses one root environment file, one Compose file, one persistent database volume, and only two helper scripts.

The target startup chain is:

```text
PostgreSQL healthy
  -> API migration
  -> deterministic API seed
  -> API process starts and /health becomes healthy
  -> agent starts and /health becomes healthy
  -> frontend starts on port 5173
```

Container creation is not readiness. Compose health checks and conditional dependencies enforce the chain above.

## 1. Files introduced in this phase

```text
Ops-Agent/
├── .env.example
├── .env                       # local only; copied from .env.example
├── docker-compose.yml
└── scripts/
    ├── start.sh
    └── health.sh
```

The API, agent, and frontend Dockerfiles are defined in their respective implementation guides. This guide does not redefine application source or Dockerfiles.

The two scripts have distinct purposes:

- `start.sh` validates configuration, builds the three application images, starts the stack, and delegates readiness checking.
- `health.sh` waits for all four services and prints useful diagnostics on failure.

A reset script is deliberately omitted. Deleting the database volume should remain an explicit command because it destroys data.

## 2. Root environment contract

Create `.env.example` with the following complete contents:

```dotenv
# PostgreSQL bootstrap identity
POSTGRES_USER=opsagent
POSTGRES_PASSWORD=localdev
POSTGRES_DB=opsagent

# Host-side published ports
POSTGRES_PORT=5432
API_PORT=8000
AGENT_PORT=8001
FRONTEND_PORT=5173

# API database connection (Docker-internal hostname)
DATABASE_URL=postgresql+psycopg://opsagent:localdev@db:5432/opsagent

# Agent checkpoint connection and isolated schema
CHECKPOINT_DATABASE_URL=postgresql://opsagent:localdev@db:5432/opsagent
CHECKPOINT_SCHEMA=agent_checkpoints

# Agent-to-API connection (Docker-internal hostname)
API_BASE_URL=http://api:8000

# Agent HTTP safety bounds
API_TIMEOUT_SECONDS=3
API_RETRY_DELAY_SECONDS=.1

# Agent graph safety bounds
MAX_TOOL_ROUNDS=4
RECURSION_LIMIT=30

# Browser-to-agent connection, embedded by Vite at image build time
VITE_AGENT_URL=http://localhost:8001

# Required for real model calls
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-6

# Application logging
LOG_LEVEL=INFO

# Optional LangSmith tracing
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=ops-agent
```

Then create the ignored local file:

```bash
cp .env.example .env
```

Set `ANTHROPIC_API_KEY` in `.env` before starting the full stack.

### Why each setting exists

`POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`
: These are consumed by the official `postgres:16` image only when it initializes an empty volume. Changing them later does not rewrite credentials in an existing database.

`POSTGRES_PORT`
: Publishes PostgreSQL to the host for local inspection and migration debugging. Containers always use `db:5432`; changing this value changes only the host-side port.

`API_PORT`, `AGENT_PORT`, and `FRONTEND_PORT`
: Control host-side bindings. Container ports remain `8000`, `8001`, and `5173`, so Docker-internal URLs do not change when a host port changes.

`DATABASE_URL`
: The synchronous SQLAlchemy/Psycopg 3 URL used by the API. The `+psycopg` dialect marker is appropriate for SQLAlchemy.

`CHECKPOINT_DATABASE_URL`
: The libpq-style PostgreSQL URL used by the agent's Psycopg pool and `AsyncPostgresSaver`. It intentionally does not use SQLAlchemy's `+psycopg` dialect marker.

`CHECKPOINT_SCHEMA`
: Names the schema used only for LangGraph checkpoint tables. The domain migration owns business tables in `public`; the agent checkpointer owns tables in `agent_checkpoints`.

`API_BASE_URL`
: Used inside the agent container. Docker DNS resolves the Compose service name `api`; `localhost` here would incorrectly point back to the agent container.

`API_TIMEOUT_SECONDS`
: Caps each agent-to-API HTTP attempt at three seconds so a stalled domain lookup cannot hold a graph turn indefinitely.

`API_RETRY_DELAY_SECONDS`
: Waits briefly before the API client's one bounded retry. The corrected Phase 2 client retries only transport/time-out failures and HTTP `502`, `503`, or `504`; it does not retry validation or other application errors.

`MAX_TOOL_ROUNDS`
: Sets the graph's soft tool-cycle cap. At the default of four, completed tool results route through the no-tools finalizer instead of allowing another lookup cycle.

`RECURSION_LIMIT`
: Sets LangGraph's top-level hard recursion guard. It must remain comfortably above the nodes required by `MAX_TOOL_ROUNDS`; it is an emergency bound, not the normal soft-limit user experience.

`VITE_AGENT_URL`
: Used by browser JavaScript. The browser runs on the host and cannot resolve the Docker service name `agent`, so this must normally be `http://localhost:8001`.

`ANTHROPIC_API_KEY`
: Required by the agent for real model calls. It is passed only to the agent container.

`ANTHROPIC_MODEL`
: Selects the model used by the normal tool-bound node and the unbound finalizer. Keeping it in the root environment makes the full-stack model choice explicit.

`LOG_LEVEL`
: Controls agent application logging. `INFO` is appropriate for the local lab; secrets, request bodies, prompts, and raw tool results must not be logged.

`LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, and `LANGSMITH_PROJECT`
: Optional tracing controls recognized by the LangSmith integration. Keep tracing disabled and the key empty for ordinary local work.

### URL and password consistency

The password appears in three places: `POSTGRES_PASSWORD`, `DATABASE_URL`, and `CHECKPOINT_DATABASE_URL`. If it changes before first startup, update all three values.

For this local lab, use an alphanumeric password so the URLs remain unambiguous. A password containing `@`, `:`, `/`, `?`, `#`, or `%` must be percent-encoded in both URLs. Do not solve that problem by committing the real password.

### Shared root environment without indiscriminate secret sharing

Compose automatically reads the root `.env` for `${...}` interpolation when commands run from the repository root. The Compose file below passes only the variables each container needs:

- PostgreSQL receives only its bootstrap identity.
- The API receives only `DATABASE_URL`.
- The agent receives its API URL, timeout/retry controls, checkpoint settings, graph limits, model settings, log level, and optional tracing settings.
- The frontend receives only `VITE_AGENT_URL` as a build argument.

This preserves the simplicity of one root environment file without exposing the Anthropic key to every container.

## 3. Compose orchestration

Replace the root `docker-compose.yml` with the following complete contents:

```yaml
name: ops-agent

services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: ${POSTGRES_USER:?Set POSTGRES_USER in .env}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in .env}
      POSTGRES_DB: ${POSTGRES_DB:?Set POSTGRES_DB in .env}
    ports:
      - "127.0.0.1:${POSTGRES_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test:
        [
          "CMD-SHELL",
          "pg_isready -U \"$$POSTGRES_USER\" -d \"$$POSTGRES_DB\"",
        ]
      interval: 3s
      timeout: 3s
      retries: 20
      start_period: 5s
    restart: unless-stopped

  api:
    build:
      context: ./api
    environment:
      DATABASE_URL: ${DATABASE_URL:?Set DATABASE_URL in .env}
    command:
      - sh
      - -ec
      - |
        alembic upgrade head
        python -m app.seed
        exec uvicorn app.main:app --host 0.0.0.0 --port 8000
    ports:
      - "127.0.0.1:${API_PORT:-8000}:8000"
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test:
        [
          "CMD",
          "python",
          "-c",
          "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).read()",
        ]
      interval: 5s
      timeout: 3s
      retries: 20
      start_period: 15s
    restart: unless-stopped

  agent:
    build:
      context: ./agent
    environment:
      API_BASE_URL: ${API_BASE_URL:-http://api:8000}
      API_TIMEOUT_SECONDS: ${API_TIMEOUT_SECONDS:-3}
      API_RETRY_DELAY_SECONDS: ${API_RETRY_DELAY_SECONDS:-.1}
      CHECKPOINT_DATABASE_URL: ${CHECKPOINT_DATABASE_URL:?Set CHECKPOINT_DATABASE_URL in .env}
      CHECKPOINT_SCHEMA: ${CHECKPOINT_SCHEMA:-agent_checkpoints}
      MAX_TOOL_ROUNDS: ${MAX_TOOL_ROUNDS:-4}
      RECURSION_LIMIT: ${RECURSION_LIMIT:-30}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:?Set ANTHROPIC_API_KEY in .env}
      ANTHROPIC_MODEL: ${ANTHROPIC_MODEL:-claude-sonnet-4-6}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      LANGSMITH_TRACING: ${LANGSMITH_TRACING:-false}
      LANGSMITH_API_KEY: ${LANGSMITH_API_KEY:-}
      LANGSMITH_PROJECT: ${LANGSMITH_PROJECT:-ops-agent}
    ports:
      - "127.0.0.1:${AGENT_PORT:-8001}:8001"
    depends_on:
      db:
        condition: service_healthy
      api:
        condition: service_healthy
    healthcheck:
      test:
        [
          "CMD",
          "python",
          "-c",
          "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=2).read()",
        ]
      interval: 5s
      timeout: 3s
      retries: 20
      start_period: 15s
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      args:
        VITE_AGENT_URL: ${VITE_AGENT_URL:-http://localhost:8001}
    ports:
      - "127.0.0.1:${FRONTEND_PORT:-5173}:5173"
    depends_on:
      agent:
        condition: service_healthy
    healthcheck:
      test:
        [
          "CMD-SHELL",
          "wget -q -O /dev/null http://127.0.0.1:5173/",
        ]
      interval: 5s
      timeout: 3s
      retries: 20
      start_period: 10s
    restart: unless-stopped

volumes:
  postgres_data:
```

### Compose design decisions

#### One PostgreSQL instance, two schemas

Both database URLs point to the same database. Alembic creates and retains every business table and enum in `public`; `CHECKPOINT_SCHEMA` is not an API migration target.

During agent lifespan startup, the corrected Phase 2 implementation first executes an identifier-quoted `CREATE SCHEMA IF NOT EXISTS agent_checkpoints`, then applies `agent_checkpoints, public` as the pool's per-connection `search_path`, and finally runs `AsyncPostgresSaver.setup()`. The saver therefore creates only checkpoint tables in `agent_checkpoints`. No manual `psql` command or Compose init SQL is required for a clean startup.

This is schema-level organization, not a strong security boundary: the shared local database role can technically access both schemas. The agent application still reads domain data only through `API_BASE_URL`; no agent tool or repository code should query business tables. Separate roles and grants are appropriate future hardening, but unnecessary for this local portfolio target.

#### Migration and seed before API readiness

The API command is deliberately sequential:

```text
alembic upgrade head
python -m app.seed
uvicorn ...
```

`sh -e` stops immediately if migration or seeding fails. `exec` makes Uvicorn the container's main process so Docker signals reach it directly.

The seed implementation from the API guide is a deterministic local-data rebuild:

- it truncates the three business tables and restarts their identities,
- the fixed seed and base time produce the same records and IDs on every run,
- it verifies the open-checkout/status invariant before committing,
- rerunning it replaces the demo dataset rather than appending duplicates.

This destructive reseed is appropriate only for the read-only portfolio dataset. Every API container start restores the canonical demo state; do not reuse this startup command for an environment containing user-owned data.

Because Uvicorn starts only after migration and seed succeed, `/health` cannot become healthy too early. The agent waits for API health, and the frontend waits for agent health.

Running migrations in the API startup command is intentionally optimized for one local API replica. A multi-replica deployment would use a separate one-shot migration job to avoid concurrent migration attempts.

#### Health checks test the real service boundary

- PostgreSQL uses `pg_isready`.
- API and agent health checks call their documented `/health` endpoints.
- The frontend fetches `/` from its Nginx server.

The API `/health` implementation verifies database connectivity. The agent app does not accept HTTP traffic until FastAPI lifespan has created the checkpoint schema, opened its Psycopg pool, initialized the saver, and compiled the graph; its `/health` route can therefore return `{"status":"ok"}` once reachable.

Health checks use tools already present in their images: Python in API/agent and BusyBox `wget` in the expected Nginx Alpine frontend image. No package is installed solely for health checking.

#### Local-only published ports

Every published port is bound to `127.0.0.1`. Other devices on the network cannot connect directly. Containers communicate over the private Compose network using service names and container ports.

The database port is exposed only for convenient local inspection. Remove the `db.ports` section if host database access is not needed.

#### Persistent database state

`postgres_data` is a named volume. These commands preserve it:

```bash
docker compose stop
docker compose down
docker compose up -d
```

Only `docker compose down --volumes` deletes it.

#### Restart policy

`unless-stopped` restarts long-running services after an unexpected exit or Docker restart. It does not hide a broken initial migration: a failing API will remain visibly unhealthy/restarting, and its logs retain the actual migration or seed error.

#### No obsolete Compose version field

Modern Docker Compose follows the Compose Specification and warns that a top-level `version` field is obsolete. The `name` field gives containers, networks, and volumes a stable `ops-agent` project prefix.

## 4. Vite's build-time URL

`VITE_AGENT_URL` is not a runtime container setting. Vite replaces it in the JavaScript bundle during `npm run build`.

The frontend Dockerfile from the frontend guide must declare the argument before building:

```text
ARG VITE_AGENT_URL
ENV VITE_AGENT_URL=$VITE_AGENT_URL
RUN npm run build
```

Those lines are shown only as the required integration contract; use the complete Dockerfile in the frontend guide.

The correct default is:

```dotenv
VITE_AGENT_URL=http://localhost:8001
```

Do not use `http://agent:8001`. That hostname is resolvable only by containers, while the compiled frontend code executes in the user's browser.

After changing `VITE_AGENT_URL`, rebuild the frontend image:

```bash
docker compose build --no-cache frontend
docker compose up -d frontend
```

A simple container restart cannot change a URL already embedded in the bundle.

The browser request crosses origins from `http://localhost:5173` to `http://localhost:8001`. The agent implementation must therefore allow the exact local frontend origin through CORS. Keep that allowlist narrow; `*` is not needed for this lab.

## 5. Startup helper

Create `scripts/start.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "error: Docker is not installed or is not on PATH" >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "error: Docker Compose v2 is required" >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "error: Docker is not running" >&2
  exit 1
fi

if [[ ! -s .env ]]; then
  echo "error: create .env with: cp .env.example .env" >&2
  exit 1
fi

if ! grep -Eq '^ANTHROPIC_API_KEY=.+$' .env; then
  echo "error: set ANTHROPIC_API_KEY in .env" >&2
  exit 1
fi

docker compose config --quiet
docker compose up --build --detach

exec bash "$ROOT_DIR/scripts/health.sh"
```

Why this script is useful:

- It always runs Compose from the repository root, so the correct `.env` is loaded.
- It fails early for common workstation setup errors.
- `docker compose config --quiet` validates interpolation and YAML before creating containers.
- It does not print the rendered configuration, which could expose secrets.
- It delegates all waiting and diagnostics to one reusable health script.

The key check expects the conventional one-line dotenv form `ANTHROPIC_API_KEY=value`. Do not quote a multi-line secret or add spaces around `=`.

## 6. Health helper

Create `scripts/health.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-120}"
DEADLINE="$(( $(date +%s) + TIMEOUT_SECONDS ))"

timed_out() {
  [[ "$(date +%s)" -ge "$DEADLINE" ]]
}

show_failure() {
  local service="$1"
  echo
  echo "error: $service did not become ready within ${TIMEOUT_SECONDS}s" >&2
  docker compose ps
  docker compose logs --no-color --tail=100 "$service" >&2
  exit 1
}

echo -n "Waiting for PostgreSQL"
until docker compose exec -T db sh -ec \
  'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  >/dev/null 2>&1; do
  timed_out && show_failure db
  echo -n "."
  sleep 2
done
echo " ready"

wait_for_http() {
  local service="$1"
  local container_port="$2"
  local path="$3"
  local address

  echo -n "Waiting for $service"
  while true; do
    address="$(docker compose port "$service" "$container_port" 2>/dev/null || true)"
    if [[ -n "$address" ]] &&
      curl --fail --silent --show-error \
        --max-time 2 "http://${address}${path}" >/dev/null 2>&1; then
      echo " ready"
      return
    fi

    timed_out && show_failure "$service"
    echo -n "."
    sleep 2
  done
}

wait_for_http api 8000 /health
wait_for_http agent 8001 /health
wait_for_http frontend 5173 /

FRONTEND_ADDRESS="$(docker compose port frontend 5173)"

echo
docker compose ps
echo
echo "Ops Agent is ready at http://${FRONTEND_ADDRESS}"
```

This script derives host addresses from `docker compose port`; it does not parse or source `.env`, and therefore never executes dotenv content as shell code. It requires `curl` on the host, which is available by default on macOS and common Linux development environments.

Neither helper assumes that values from `.env` are exported into the calling shell. `start.sh` lets Compose read the root file for interpolation, while `health.sh` discovers published ports through Compose and expands PostgreSQL variables only inside the database container.

`HEALTH_TIMEOUT_SECONDS` is a temporary shell override, not an application secret:

```bash
HEALTH_TIMEOUT_SECONDS=240 ./scripts/health.sh
```

Make both scripts executable:

```bash
chmod +x scripts/start.sh scripts/health.sh
```

## 7. Daily commands

### Start or rebuild

```bash
./scripts/start.sh
```

For an unchanged stack:

```bash
docker compose up -d
./scripts/health.sh
```

### Inspect status and logs

```bash
docker compose ps
docker compose logs -f api
docker compose logs -f agent
docker compose logs -f frontend
docker compose logs -f db
```

Follow all logs together:

```bash
docker compose logs -f
```

### Stop while preserving data

```bash
docker compose down
```

### Restart one service

```bash
docker compose restart agent
./scripts/health.sh
```

Use recreation, not restart, after changing `.env`:

```bash
docker compose up -d --force-recreate api agent
./scripts/health.sh
```

Rebuild after changing source, dependencies, Dockerfiles, or `VITE_AGENT_URL`:

```bash
docker compose up -d --build
./scripts/health.sh
```

## 8. Reset and recovery

### Full destructive reset

This deletes domain records and LangGraph conversation checkpoints:

```bash
docker compose down --volumes --remove-orphans
./scripts/start.sh
```

The `--volumes` flag is the destructive part. The next startup initializes PostgreSQL, migrates the domain schema, reseeds deterministic demo data, and recreates checkpoint tables.

### Rerun migration and seed explicitly

If API startup failed, inspect the error first:

```bash
docker compose logs --tail=200 api
```

Then rerun each step in a disposable API container:

```bash
docker compose run --rm api alembic upgrade head
docker compose run --rm api python -m app.seed
docker compose up -d api agent frontend
./scripts/health.sh
```

These commands override the API service's normal startup command. They still use the same image, network, and `DATABASE_URL`.

Do not automatically run `alembic downgrade` after a migration failure. Determine whether the failed migration committed any changes, correct the migration, and rerun `upgrade head`. PostgreSQL transactions protect many DDL operations, but an assumed rollback is not a recovery plan.

### Reset only agent conversation history

For the default names, this removes only the checkpoint schema:

```bash
docker compose stop agent
docker compose exec -T db \
  psql -U opsagent -d opsagent \
  -c 'DROP SCHEMA IF EXISTS agent_checkpoints CASCADE;'
docker compose start agent
./scripts/health.sh
```

If `.env` uses different database or schema names, replace the names in this command. On restart, agent lifespan recreates `agent_checkpoints` and its checkpointer tables before `/health` becomes reachable. Business tables in `public` and their seeded data remain intact.

### Credentials changed after the volume was created

Editing `POSTGRES_PASSWORD` does not update an existing database role. For disposable local data, perform the full destructive reset. If data must be kept, change the role password inside PostgreSQL first and then update both connection URLs.

### Port already in use

Change only the relevant host-side port in `.env`, for example:

```dotenv
AGENT_PORT=18001
VITE_AGENT_URL=http://localhost:18001
```

Because the Vite URL changed, rebuild the frontend:

```bash
docker compose up -d --build agent frontend
```

Internal service URLs remain `http://api:8000` and the checkpoint database host remains `db:5432`.

### Back up the local database

Before experimenting with a non-disposable volume:

```bash
docker compose exec -T db \
  sh -ec 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  > ops-agent-backup.sql
```

The backup file may contain portfolio data and checkpoint content. Keep it out of Git.

## 9. Readiness troubleshooting

### Database is unhealthy

Check:

```bash
docker compose logs db
docker compose exec db sh -ec \
  'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Common causes are a stale volume initialized with different credentials, a host port collision, or an invalid local Docker state.

### API never becomes healthy

Check:

```bash
docker compose logs api
```

The most likely failures occur before Uvicorn starts:

- `DATABASE_URL` credentials do not match the initialized volume.
- Alembic cannot locate its configuration or migration.
- The migration fails.
- The deterministic seed fails while rebuilding data or checking its invariant.
- `/health` does not verify and report database readiness correctly.

Do not make the health check return success to conceal migration or seed failures.

### Agent never becomes healthy

Check:

```bash
docker compose logs agent
curl -i http://localhost:8000/health
```

Common causes are:

- missing or invalid `ANTHROPIC_API_KEY`,
- an invalid `CHECKPOINT_DATABASE_URL`,
- failure during the agent-owned creation or per-connection selection of `CHECKPOINT_SCHEMA`,
- the API is healthy at `/health` but its required routes do not match the agent tools,
- agent lifespan initialization did not complete.

### Frontend loads but chat requests fail

Inspect the browser network panel and verify:

```bash
curl -i http://localhost:8001/health
```

Then confirm:

- the compiled `VITE_AGENT_URL` uses a host-visible URL,
- the frontend image was rebuilt after changing it,
- the agent allows `http://localhost:5173` through CORS,
- the browser is not trying to resolve `api` or `agent`.

## 10. From-zero four-service lab

This lab assumes the API, agent, and frontend guides have been completed, including all three Dockerfiles.

### Step 1: create local configuration

From the repository root:

```bash
cp .env.example .env
```

Edit `.env`, set a real `ANTHROPIC_API_KEY`, and leave tracing disabled for the first run.

### Step 2: validate without revealing rendered secrets

```bash
docker compose config --quiet
```

Do not paste the output of plain `docker compose config` into issues or chat; rendered environment values can contain secrets.

### Step 3: start from an empty database

If this repository has been run before and its data is disposable:

```bash
docker compose down --volumes --remove-orphans
```

Then:

```bash
chmod +x scripts/start.sh scripts/health.sh
./scripts/start.sh
```

Expected result: all four services are listed as running, and `db`, `api`, `agent`, and `frontend` become healthy.

### Step 4: prove migration and seed ordering

```bash
docker compose logs api
```

The log order must show:

1. Alembic reaches the latest revision.
2. The deterministic seed completes.
3. Uvicorn begins listening on `0.0.0.0:8000`.
4. API health checks begin succeeding.

Run the seed again to prove deterministic rebuilding:

```bash
docker compose run --rm api python -m app.seed
```

It should report the same fixed counts and seed, restart IDs predictably, and create no duplicate users, assets, or checkouts.

### Step 5: inspect schema separation

Using the example database names:

```bash
docker compose exec -T db \
  psql -U opsagent -d opsagent \
  -c '\dn'

docker compose exec -T db \
  psql -U opsagent -d opsagent \
  -c '\dt public.*'

docker compose exec -T db \
  psql -U opsagent -d opsagent \
  -c '\dt agent_checkpoints.*'
```

Expected result:

- domain tables such as assets, users, and checkouts are in `public`,
- LangGraph checkpoint tables are in `agent_checkpoints`,
- there is still only one PostgreSQL database service.

The presence of `agent_checkpoints` after this clean startup proves that agent lifespan created it; the lab does not pre-create the schema.

### Step 6: verify service boundaries

```bash
curl --fail http://localhost:8000/health
curl --fail http://localhost:8001/health
curl --fail http://localhost:5173/
```

Expected API and agent health responses report a ready/healthy status according to their guides. The frontend request returns HTML.

### Step 7: verify a chat request

Use a fresh UUID:

```bash
THREAD_ID="$(python -c 'import uuid; print(uuid.uuid4())')"

curl --fail \
  --header 'Content-Type: application/json' \
  --data "{\"message\":\"Find stale laptops assigned to Engineering.\",\"thread_id\":\"${THREAD_ID}\"}" \
  http://localhost:8001/chat
```

The response must contain:

```json
{
  "answer": "A final user-facing answer",
  "thread_id": "the UUID sent in the request",
  "tool_rounds": 1,
  "soft_limit_reached": false
}
```

The exact answer and tool-round count can vary with model behavior. The field names and types cannot.

### Step 8: prove persistence

Stop and restart without deleting the volume:

```bash
docker compose down
docker compose up -d
./scripts/health.sh
```

Send a follow-up message with the same `THREAD_ID`. The agent should resume the checkpointed conversation, and the deterministic domain data should still be present.

## 11. Completion checklist

- [ ] `.env.example` contains no real secret.
- [ ] `.env` exists, is ignored by Git, and contains the local Anthropic key.
- [ ] Both database URLs use `db:5432` and consistent credentials.
- [ ] `DATABASE_URL` uses SQLAlchemy's `postgresql+psycopg://` form.
- [ ] `CHECKPOINT_DATABASE_URL` uses the Psycopg-compatible `postgresql://` form.
- [ ] Business tables remain in `public`; `CHECKPOINT_SCHEMA=agent_checkpoints`.
- [ ] Agent lifespan creates `agent_checkpoints` before saver setup on a clean database.
- [ ] `API_BASE_URL`, `API_TIMEOUT_SECONDS`, and `API_RETRY_DELAY_SECONDS` match the Phase 2 settings aliases.
- [ ] `MAX_TOOL_ROUNDS` and `RECURSION_LIMIT` use the Phase 2 names and safe defaults.
- [ ] The API migrates and deterministically seeds before Uvicorn starts.
- [ ] The API reports healthy only after database readiness.
- [ ] The agent reports healthy only after checkpoint and graph initialization.
- [ ] The frontend waits for agent health.
- [ ] `VITE_AGENT_URL` is host-visible and embedded during the frontend build.
- [ ] All published ports bind to `127.0.0.1`.
- [ ] `postgres_data` survives ordinary `docker compose down`.
- [ ] The start and health helpers succeed from the repository root.
- [ ] Rerunning the seed reconstructs the same canonical dataset without duplicates.
- [ ] A repeated `thread_id` survives a non-destructive Compose restart.
