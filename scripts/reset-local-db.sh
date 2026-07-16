#!/usr/bin/env bash
# Destructive reset: deletes the local PostgreSQL volume (business data and
# LangGraph checkpoints), then lets the next `docker compose up` recreate a
# clean schema and reseed deterministic demo data. Requires an explicit
# confirmation so this never runs by accident.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ "${1:-}" != "--yes" ]]; then
  echo "This deletes the local Postgres volume (business data and agent"
  echo "conversation checkpoints). It cannot be undone."
  read -r -p "Type 'delete' to continue: " confirmation
  if [[ "$confirmation" != "delete" ]]; then
    echo "Aborted; nothing was deleted." >&2
    exit 1
  fi
fi

docker compose down --volumes --remove-orphans
echo "Local database volume removed. Run 'docker compose up -d' to recreate it."
