#!/bin/bash

# Wrapper to run the Syndicate LLM worker inside project venv
set -euo pipefail

# Determine project directory
if [ -d "/mnt/disk/syndicate" ]; then
    SYNDICATE_DIR="/mnt/disk/syndicate"
else
    SYNDICATE_DIR="/home/adam/worxpace/syndicate"
fi

cd "$SYNDICATE_DIR" || exit 1

# Load env files (project .env then .gemini overrides)
if [ -f "$SYNDICATE_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$SYNDICATE_DIR/.env"
    set +a
fi
if [ -f "$SYNDICATE_DIR/.gemini/env.sh" ]; then
    # shellcheck disable=SC1090
    source "$SYNDICATE_DIR/.gemini/env.sh"
fi

# Activate venv
source ".venv/bin/activate"

# Run worker
exec python scripts/llm_worker.py
