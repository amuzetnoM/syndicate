#!/bin/bash

# Define the Syndicate project directory (use /mnt/disk if mounted, otherwise fallback to workspace path)
if [ -d "/mnt/disk/syndicate" ]; then
    GOLD_STANDARD_DIR="/mnt/disk/syndicate"
elif [ -d "/home/adam/worxpace/syndicate" ]; then
    GOLD_STANDARD_DIR="/home/adam/worxpace/syndicate"
else
    echo "Syndicate directory not found at /mnt/disk/syndicate or /home/adam/worxpace/syndicate" && exit 1
fi
VENV_DIR="${GOLD_STANDARD_DIR}/.venv"
RUN_PY_PATH="${GOLD_STANDARD_DIR}/run.py"
REQUIREMENTS_FILE="${GOLD_STANDARD_DIR}/requirements.txt"

# Change to the Syndicate directory
cd "$GOLD_STANDARD_DIR" || { echo "Failed to change directory to $GOLD_STANDARD_DIR"; exit 1; }

# Load project .env (export variables for child processes)
if [ -f "$GOLD_STANDARD_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$GOLD_STANDARD_DIR/.env"
    set +a
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR" || { echo "Failed to create virtual environment"; exit 1; }
fi

# Activate the virtual environment
source "$VENV_DIR/bin/activate" || { echo "Failed to activate virtual environment"; exit 1; }

# Install dependencies if requirements.txt exists
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "Installing dependencies from $REQUIREMENTS_FILE..."
    if ! pip install -r "$REQUIREMENTS_FILE"; then
        echo "Failed to install dependencies";
        exit 1
    fi
fi

# Source canonical secret store (.gemini/env.sh) if present (permissions 600 expected)
if [ -f "$GOLD_STANDARD_DIR/.gemini/env.sh" ]; then
    # shellcheck disable=SC1090
    source "$GOLD_STANDARD_DIR/.gemini/env.sh"
fi

# Configure Ollama and LLM timeouts to avoid long blocking generations
export OLLAMA_PING_TIMEOUT_S=${OLLAMA_PING_TIMEOUT_S:-2}
export OLLAMA_LIST_TIMEOUT_S=${OLLAMA_LIST_TIMEOUT_S:-5}
export OLLAMA_TIMEOUT_S=${OLLAMA_TIMEOUT_S:-120}
export GOLDSTANDARD_LLM_TIMEOUT=${GOLDSTANDARD_LLM_TIMEOUT:-120}

# Execute run.py with --once and wait flags to ensure publishing completes
echo "Running $RUN_PY_PATH --once --wait..."
python "$RUN_PY_PATH" --once --wait || { echo "Failed to execute run.py --once --wait"; exit 1; }

deactivate # Deactivate virtual environment
