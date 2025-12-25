#!/bin/bash
# Syndicate - Automated Setup Script (Unix/macOS/Linux)
# Run with: chmod +x setup.sh && ./setup.sh
# Auto-installs Python 3.12 via brew (macOS) or apt/dnf (Linux) if needed

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo "========================================"
echo "   Syndicate - Automated Setup"
echo "========================================"
echo ""

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ -f /etc/debian_version ]]; then
        echo "debian"
    elif [[ -f /etc/redhat-release ]]; then
        echo "redhat"
    elif [[ -f /etc/arch-release ]]; then
        echo "arch"
    else
        echo "unknown"
    fi
}

OS_TYPE=$(detect_os)
echo -e "      Detected OS: ${CYAN}$OS_TYPE${NC}"

# Function to check Python version compatibility
check_python_version() {
    local python_cmd=$1
    if command -v $python_cmd &> /dev/null; then
        local version=$($python_cmd --version 2>&1 | grep -oP '\\d+\\.\\d+' | head -1)
        local major=$(echo $version | cut -d. -f1)
        local minor=$(echo $version | cut -d. -f2)
        if [[ $major -eq 3 && $minor -ge 10 && $minor -le 13 ]]; then
            echo $python_cmd
            return 0
        fi
    fi
    return 1
}

# Function to find best Python command
find_python() {
    # Priority: python3.12 > python3.11 > python3.10 > python3.13 > python3
    for ver in python3.12 python3.11 python3.10 python3.13; do
        if result=$(check_python_version $ver); then
            echo $result
            return 0
        fi
    done

    # Try generic python3
    if result=$(check_python_version python3); then
        echo $result
        return 0
    fi

    return 1
}

# Function to install Python based on OS
install_python() {
    echo -e "      ${CYAN}Attempting automatic Python 3.12 installation...${NC}"

    case $OS_TYPE in
        macos)
            if command -v brew &> /dev/null; then
                echo -e "      ${CYAN}Installing via Homebrew...${NC}"
                brew install python@3.12
                # Add to PATH for this session
                export PATH="/opt/homebrew/opt/python@3.12/bin:/usr/local/opt/python@3.12/bin:$PATH"
                return 0
            else
                echo -e "      ${YELLOW}Homebrew not found. Installing Homebrew first...${NC}"
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                # Try to configure Homebrew path
                if [[ -f "/opt/homebrew/bin/brew" ]]; then
                    eval "$(/opt/homebrew/bin/brew shellenv)"
                elif [[ -f "/usr/local/bin/brew" ]]; then
                    eval "$(/usr/local/bin/brew shellenv)"
                fi
                brew install python@3.12
                export PATH="/opt/homebrew/opt/python@3.12/bin:/usr/local/opt/python@3.12/bin:$PATH"
                return 0
            fi
            ;;
        debian)
            echo -e "      ${CYAN}Installing via apt...${NC}"
            sudo apt update
            sudo apt install -y python3.12 python3.12-venv python3.12-dev python3-pip
            return 0
            ;;
        redhat)
            echo -e "      ${CYAN}Installing via dnf...${NC}"
            sudo dnf install -y python3.12 python3.12-devel python3-pip
            return 0
            ;;
        arch)
            echo -e "      ${CYAN}Installing via pacman...${NC}"
            sudo pacman -Sy --noconfirm python python-pip
            return 0
            ;;
        *)
            echo -e "      ${RED}Unsupported OS for automatic installation.${NC}"
            return 1
            ;;
    esac
}

# Check Python installation
echo -e "[1/8] Checking Python installation..."

PYTHON_CMD=$(find_python) || PYTHON_CMD=""

if [[ -z "$PYTHON_CMD" ]]; then
    echo -e "      ${YELLOW}No compatible Python (3.10-3.13) found.${NC}"

    if install_python; then
        sleep 2
        PYTHON_CMD=$(find_python) || PYTHON_CMD=""
        if [[ -z "$PYTHON_CMD" ]]; then
            echo -e "      ${YELLOW}Please restart your terminal and run this script again.${NC}"
            exit 0
        fi
    else
        echo -e "      ${RED}ERROR: Automatic installation failed.${NC}"
        echo -e "      ${YELLOW}Please install Python 3.12 manually:${NC}"
        case $OS_TYPE in
            macos)
                echo "        brew install python@3.12"
                ;;
            debian)
                echo "        sudo apt install python3.12 python3.12-venv"
                ;;
            redhat)
                echo "        sudo dnf install python3.12"
                ;;
            *)
                echo "        Visit: https://www.python.org/downloads/"
                ;;
        esac
        exit 1
    fi
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo -e "      ${GREEN}Using: $PYTHON_VERSION ($PYTHON_CMD)${NC}"

# Create virtual environment (prefer venv312 for numba support)
echo -e "[2/8] Creating virtual environment..."
VENV_DIR="venv312"
if [ -d "$VENV_DIR" ]; then
    echo -e "      ${YELLOW}Virtual environment '$VENV_DIR' already exists. Skipping creation.${NC}"
elif [ -d ".venv" ]; then
    echo -e "      ${YELLOW}Found legacy .venv - recommend migrating to venv312 for numba support.${NC}"
    VENV_DIR=".venv"
else
    $PYTHON_CMD -m venv $VENV_DIR
    echo -e "      ${GREEN}Created $VENV_DIR successfully.${NC}"
fi

# Activate virtual environment
echo -e "[3/8] Activating virtual environment..."
source $VENV_DIR/bin/activate
echo -e "      ${GREEN}Activated $VENV_DIR${NC}"

# Upgrade pip first
echo -e "[4/8] Upgrading pip..."
python -m pip install --upgrade pip --quiet
echo -e "      ${GREEN}pip upgraded${NC}"

# Install dependencies
echo -e "[5/8] Installing production dependencies..."
pip install -r requirements.txt --quiet
echo -e "      ${GREEN}Installed requirements.txt${NC}"

# Install dev dependencies (optional)
echo -e "[6/8] Installing development dependencies..."
if [ -f "requirements-dev.txt" ]; then
    pip install -r requirements-dev.txt --quiet
    echo -e "      ${GREEN}Installed requirements-dev.txt${NC}"
else
    echo -e "      ${YELLOW}Skipped (requirements-dev.txt not found)${NC}"
fi

# Ollama setup and model downloads
echo -e "[7/8] Checking Ollama setup..."
if command -v ollama &> /dev/null; then
    OLLAMA_PATH=$(command -v ollama)
    echo -e "      ${GREEN}Ollama CLI detected ($OLLAMA_PATH).${NC}"
    OLLAMA_MODELS=("llama3.2")
    for model in "${OLLAMA_MODELS[@]}"; do
        echo -e "      ${CYAN}Pulling Ollama model '$model'...${NC}"
        if ollama pull "$model"; then
            echo -e "      ${GREEN}Ollama model '$model' ready.${NC}"
        else
            echo -e "      ${YELLOW}WARNING: Failed to pull '$model'. Start Ollama with 'ollama serve' and retry.${NC}"
        fi
    done
else
    echo -e "      ${YELLOW}Ollama CLI not found. Skipping Ollama model download.${NC}"
    echo -e "      ${CYAN}Install Ollama from https://ollama.ai to enable the local provider.${NC}"
fi

# GGUF downloads for llama.cpp fallback
echo -e "[8/8] Downloading GGUF models..."

GGUF_DIR="$HOME/.cache/syndicate/models"
mkdir -p "$GGUF_DIR"

GGUF_FILE="$GGUF_DIR/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
EXPECTED_SIZE=4370000000  # ~4.37 GB

if [ -f "$GGUF_FILE" ]; then
    CURRENT_SIZE=$(stat -f%z "$GGUF_FILE" 2>/dev/null || stat -c%s "$GGUF_FILE" 2>/dev/null || echo 0)
    THRESHOLD=$((EXPECTED_SIZE * 95 / 100))
    if [ "$CURRENT_SIZE" -ge "$THRESHOLD" ]; then
        SIZE_GB=$(echo "scale=2; $CURRENT_SIZE / 1073741824" | bc)
        echo -e "      ${GREEN}GGUF model already downloaded (${SIZE_GB} GB)${NC}"
    else
        SIZE_GB=$(echo "scale=2; $CURRENT_SIZE / 1073741824" | bc)
        echo -e "      ${YELLOW}Incomplete GGUF detected (${SIZE_GB} GB / 4.37 GB)${NC}"
        echo -e "      ${CYAN}Resuming download via Python...${NC}"
        python scripts/local_llm.py --download mistral-7b
    fi
else
    echo -e "      ${CYAN}Downloading Mistral 7B GGUF (4.4 GB)...${NC}"
    echo -e "      ${CYAN}This may take 10-30 minutes depending on connection.${NC}"
    if python scripts/local_llm.py --download mistral-7b; then
        echo -e "      ${GREEN}GGUF model downloaded successfully.${NC}"
    else
        echo -e "      ${YELLOW}WARNING: GGUF download may have failed. Re-run setup to retry.${NC}"
        echo -e "      ${CYAN}Manual download: python scripts/local_llm.py --download mistral-7b${NC}"
    fi
fi

# Setup .env file
echo ""
echo "----------------------------------------"
if [ ! -f ".env" ]; then
    if [ -f ".env.template" ]; then
        cp .env.template .env
        echo -e "${GREEN}Created .env from template.${NC}"
        echo -e "${YELLOW}IMPORTANT: Edit .env and add your GEMINI_API_KEY${NC}"
    fi
else
    echo -e "${GREEN}.env file already exists.${NC}"
fi

# Initialize Cortex memory
if [ ! -f "cortex_memory.json" ]; then
    if [ -f "cortex_memory.template.json" ]; then
        cp cortex_memory.template.json cortex_memory.json
        echo -e "${GREEN}Initialized cortex_memory.json from template.${NC}"
    fi
else
    echo -e "${GREEN}cortex_memory.json already exists.${NC}"
fi

# Create output directories
if [ ! -d "output" ]; then
    mkdir -p output/charts
    mkdir -p output/reports/charts
    echo -e "${GREEN}Created output directories.${NC}"
fi

# Install systemd unit files and enable services (first-run only)
if command -v systemctl &> /dev/null && [ -d "/run/systemd/system" ]; then
    if [ -d "deploy/systemd" ]; then
        if [ ! -f ".setup_systemd_done" ]; then
            echo -e "[9/9] Installing systemd unit files and enabling monitor/service units (requires sudo)..."
            sudo cp -n deploy/systemd/* /etc/systemd/system/ || echo -e "${YELLOW}WARNING: Failed to copy some unit files.${NC}"
            sudo systemctl daemon-reload
            # Enable and start monitor if unit exists
            if [ -f "/etc/systemd/system/syndicate-monitor.service" ]; then
                sudo systemctl enable --now syndicate-monitor.service || echo -e "${YELLOW}WARNING: Failed to enable/start syndicate-monitor.service${NC}"
            fi
            # Attempt to enable core services if present
            sudo systemctl enable --now syndicate-discord-bot.service syndicate-llm-worker.service syndicate-daily-llm-report.timer || true
            touch .setup_systemd_done
            echo -e "${GREEN}Systemd units installed and monitor enabled (if present).${NC}"
        else
            echo -e "${YELLOW}Systemd units already installed in a previous setup run; skipping.${NC}"
        fi
    fi
fi

echo ""
echo "========================================"
echo -e "${GREEN}   Setup Complete!${NC}"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your GEMINI_API_KEY"
echo "  2. (Optional) Start Ollama service: ollama serve"
echo "  3. Run: python run.py --mode daily --no-ai  (test without AI)"
echo "  4. Run: python run.py  (daemon mode, runs every 4 hours)"
echo "  5. Run: python gui.py  (GUI dashboard)"
echo ""
echo -e "${GREEN}Virtual environment '$VENV_DIR' is now active.${NC}"
echo "To deactivate later, run: deactivate"
echo ""
