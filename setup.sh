#!/bin/bash
# Gold Standard - Automated Setup Script (Unix/macOS/Linux)
# Run with: chmod +x setup.sh && ./setup.sh

set -e

echo ""
echo "========================================"
echo "   Gold Standard - Automated Setup"
echo "========================================"
echo ""

# Check Python installation
echo "[1/5] Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "      ERROR: Python not found. Please install Python 3.11+ first."
    exit 1
fi
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo "      Found: $PYTHON_VERSION"

# Create virtual environment
echo "[2/5] Creating virtual environment..."
if [ -d ".venv" ]; then
    echo "      Virtual environment already exists. Skipping creation."
else
    $PYTHON_CMD -m venv .venv
    echo "      Created .venv successfully."
fi

# Activate virtual environment
echo "[3/5] Activating virtual environment..."
source .venv/bin/activate
echo "      Activated .venv"

# Install dependencies
echo "[4/5] Installing production dependencies..."
pip install -r requirements.txt --quiet
echo "      Installed requirements.txt"

# Install dev dependencies (optional)
echo "[5/5] Installing development dependencies..."
if [ -f "requirements-dev.txt" ]; then
    pip install -r requirements-dev.txt --quiet
    echo "      Installed requirements-dev.txt"
else
    echo "      Skipped (requirements-dev.txt not found)"
fi

# Setup .env file
echo ""
echo "----------------------------------------"
if [ ! -f ".env" ]; then
    if [ -f ".env.template" ]; then
        cp .env.template .env
        echo "Created .env from template."
        echo "IMPORTANT: Edit .env and add your GEMINI_API_KEY"
    fi
else
    echo ".env file already exists."
fi

# Initialize Cortex memory
if [ ! -f "cortex_memory.json" ]; then
    if [ -f "cortex_memory.template.json" ]; then
        cp cortex_memory.template.json cortex_memory.json
        echo "Initialized cortex_memory.json from template."
    fi
else
    echo "cortex_memory.json already exists."
fi

# Create output directories
if [ ! -d "output" ]; then
    mkdir -p output/charts
    mkdir -p output/reports/charts
    echo "Created output directories."
fi

echo ""
echo "========================================"
echo "   Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your GEMINI_API_KEY"
echo "  2. Run: python run.py --mode daily --no-ai  (test without AI)"
echo "  3. Run: python run.py  (interactive mode)"
echo "  4. Run: python gui.py  (GUI dashboard)"
echo ""
echo "Virtual environment is now active."
echo "To deactivate later, run: deactivate"
echo ""
