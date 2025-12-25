#!/bin/bash
# Syndicate Web UI - Quick Install Script
# This script installs all necessary dependencies and starts the web UI

set -e

echo "================================================"
echo "  Syndicate Web UI - Installation"
echo "================================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Check if venv exists
if [ ! -d "venv" ] && [ ! -d ".venv" ] && [ ! -d "venv312" ]; then
    echo ""
    echo "No virtual environment found. Creating one..."
    python3 -m venv .venv
    echo "✓ Virtual environment created at .venv"
fi

# Activate venv
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "venv312" ]; then
    source venv312/bin/activate
fi

echo ""
echo "Installing web UI dependencies..."
pip install -q --upgrade pip
pip install -q Flask Flask-SocketIO python-socketio eventlet

echo "✓ Dependencies installed"
echo ""
echo "================================================"
echo "  Installation Complete!"
echo "================================================"
echo ""
echo "To start the web UI, run:"
echo ""
echo "  python web_ui/start.py"
echo ""
echo "Then open your browser to:"
echo ""
echo "  http://localhost:5000"
echo ""
echo "================================================"
