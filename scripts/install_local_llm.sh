#!/usr/bin/env bash
set -euo pipefail

# Install llama-cpp-python into the AI venv and download a small GGUF model
# Usage: ./install_local_llm.sh [--model <model-name>] [--venv /path/to/venv]

MODEL_NAME=${1:-"phi3-mini"}
VENV_PATH=${2:-"$HOME/worxpace/.venv_ai"}
TMPDIR=${TMPDIR:-$HOME/tmp}
MODELS_DIR=${MODELS_DIR:-"$HOME/.cache/syndicate/models"}
HF_TOKEN=${HF_TOKEN:-""}

echo "[LOCAL LLM] Using venv: $VENV_PATH"

if [[ ! -d "$VENV_PATH" ]]; then
  echo "[LOCAL LLM] Virtualenv not found at $VENV_PATH" >&2
  exit 1
fi

# Activate venv and install llama-cpp-python using TMPDIR to avoid /tmp issues
export TMPDIR="$TMPDIR"
source "$VENV_PATH/bin/activate"

echo "[LOCAL LLM] Installing llama-cpp-python into venv (this will compile vendor libs)"
python -m pip install --upgrade pip setuptools wheel
python -m pip install --upgrade --no-cache-dir llama-cpp-python

# Make models dir
mkdir -p "$MODELS_DIR"
cd "$MODELS_DIR"

# Attempt to download model from Hugging Face (requires HF_TOKEN for private models)
echo "[LOCAL LLM] Attempting to download GGUF model: $MODEL_NAME"
if [[ -n "$HF_TOKEN" ]]; then
  auth_header=("-H" "Authorization: Bearer $HF_TOKEN")
else
  auth_header=()
fi

# Many GGUF builds are under 'TheBloke' or 'stabilityai' — user may override via MODEL_URL env
MODEL_URL=${MODEL_URL:-"https://huggingface.co/TheBloke/phi3-mini-GGUF/resolve/main/phi3-mini.gguf"}

if curl -fSL ${auth_header[@]} -o "$MODEL_NAME.gguf" "$MODEL_URL"; then
  echo "[LOCAL LLM] Model downloaded to $MODELS_DIR/$MODEL_NAME.gguf"
else
  echo "[LOCAL LLM] Failed to download model from $MODEL_URL" >&2
  echo "[LOCAL LLM] You may need to set HF_TOKEN or MODEL_URL to a valid GGUF URL" >&2
fi

# Print instructions
echo "[LOCAL LLM] To use this local model set LOCAL_LLM_MODEL=$MODELS_DIR/$MODEL_NAME.gguf"

echo "[LOCAL LLM] Done."