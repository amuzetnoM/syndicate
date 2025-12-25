#!/usr/bin/env bash
# Lightweight runner script for containerized syndicate executor
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Load repo .env into the environment if present (best-effort)
if [ -f "$PROJECT_ROOT/.env" ]; then
  # Use shell sourcing to preserve quoted values and export all variables
  set -a
  # shellcheck disable=SC1090
  . "$PROJECT_ROOT/.env"
  set +a
fi

# Prefer project virtualenv if available
if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
  PY="$PROJECT_ROOT/.venv/bin/python"
elif [ -x "$PROJECT_ROOT/venv/bin/python" ]; then
  PY="$PROJECT_ROOT/venv/bin/python"
elif [ -x "$PROJECT_ROOT/venv312/bin/python" ]; then
  PY="$PROJECT_ROOT/venv312/bin/python"
else
  PY="$(command -v python3 || command -v python)"
fi

# Start optional metrics server in background
"$PY" scripts/metrics_server.py &
# Run executor daemon in drain mode once
"$PY" scripts/executor_daemon.py --once
