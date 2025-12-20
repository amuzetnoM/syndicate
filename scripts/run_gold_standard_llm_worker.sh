#!/bin/bash

# Wrapper to run the Gold Standard LLM worker inside project venv
set -euo pipefail

# Determine project directory
if [ -d "/mnt/disk/gold_standard" ]; then
    GOLD_STANDARD_DIR="/mnt/disk/gold_standard"
else
    GOLD_STANDARD_DIR="/home/adam/worxpace/gold_standard"
fi

cd "$GOLD_STANDARD_DIR" || exit 1

# Load env files (project .env then .gemini overrides)
if [ -f "$GOLD_STANDARD_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$GOLD_STANDARD_DIR/.env"
    set +a
fi
if [ -f "$GOLD_STANDARD_DIR/.gemini/env.sh" ]; then
    # shellcheck disable=SC1090
    source "$GOLD_STANDARD_DIR/.gemini/env.sh"
fi

# Activate venv
source ".venv/bin/activate"

# Run worker
exec python scripts/llm_worker.py
