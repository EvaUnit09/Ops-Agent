#!/usr/bin/env bash
# Canonical entrypoint name (doc 00's tree) for the read-only smoke probe.
# The actual logic lives in smoke.py so it can use Python's stdlib http
# client instead of reimplementing JSON/HTTP handling in bash.
set -euo pipefail
exec python3 "$(dirname "${BASH_SOURCE[0]}")/smoke.py" "$@"
