#!/bin/bash

# Define the Gold Standard project directory
GOLD_STANDARD_DIR="/mnt/disk/gold_standard"
VENV_DIR="${GOLD_STANDARD_DIR}/.venv"
RUN_PY_PATH="${GOLD_STANDARD_DIR}/run.py"
REQUIREMENTS_FILE="${GOLD_STANDARD_DIR}/requirements.txt"

# Change to the Gold Standard directory
cd "$GOLD_STANDARD_DIR" || { echo "Failed to change directory to $GOLD_STANDARD_DIR"; exit 1; }

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
    pip install -r "$REQUIREMENTS_FILE" || { echo "Failed to install dependencies"; exit 1; }
fi

# Execute run.py with --once argument
echo "Running $RUN_PY_PATH --once..."
python "$RUN_PY_PATH" --once || { echo "Failed to execute run.py --once"; exit 1; }

deactivate # Deactivate virtual environment
