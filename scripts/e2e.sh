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

# Captured immediately after the stack is up and before any read-only smoke
# traffic hits it, so the before/after comparison below can actually detect
# a mutation instead of comparing two post-smoke snapshots to each other.
before="$(fingerprint)"

python3 scripts/smoke.py

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
