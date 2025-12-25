# LLM Providers Guide

Syndicate v3.3.0+ supports multiple LLM backends with automatic fallback. This guide covers setup, configuration, and usage for each provider.

---

## Quick Start

### Option 1: Cloud API (Gemini)
```bash
# Set your API key and run
export GEMINI_API_KEY="YOUR_KEY_HERE"  # pragma: allowlist secret
python run.py
```

### Option 2: Local-Only (No Cloud)
```bash
# Use local llama.cpp with any GGUF model
export PREFER_LOCAL_LLM=1
export LOCAL_LLM_MODEL="./models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
python run.py
```

### Option 3: Ollama (Easiest Local Setup)
```bash
# Install and start Ollama, then run
ollama pull llama3.2
export LLM_PROVIDER=ollama
python run.py
```

---

## Provider Comparison

| Provider | Setup Complexity | Internet Required | GPU Support | Best For |
|----------|-----------------|-------------------|-------------|----------|
| **Gemini** | Easy | Yes | N/A (cloud) | Best quality, quick start |
| **Ollama** | Easy | No* | Yes | Easy local setup, model management |
| **llama.cpp** | Medium | No | Yes | Maximum control, any GGUF model |

*Ollama requires internet only for initial model download.

---

## 1. Google Gemini (Cloud)

The default provider offering high-quality responses via Google's API.

### Setup
1. Get a free API key from [Google AI Studio](https://aistudio.google.com/apikey)
2. Set the environment variable:
   ```bash
   export GEMINI_API_KEY="YOUR_KEY_HERE"  # pragma: allowlist secret
   ```

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | (required) | Your Google AI API key |
| `GEMINI_MODEL` | `models/gemini-pro-latest` | Model to use |

### Limitations
- Free tier: ~60 requests/minute
- Requires internet connection
- Data sent to Google's servers

---

## 2. Ollama (Local Server)

Ollama provides easy local model management with one-command setup.

### Setup

1. **Install Ollama:**
   - Windows: Download from [ollama.ai](https://ollama.ai)
   - macOS: `brew install ollama`
   - Linux: `curl -fsSL https://ollama.ai/install.sh | sh`

2. **Pull a model:**
   ```bash
   ollama pull llama3.2      # Recommended - fast, capable
   ollama pull mistral       # Alternative - good for analysis
   ollama pull phi3          # Smallest - 2GB, still capable
   ```

3. **Start the server:**
   ```bash
   ollama serve
   ```

4. **Configure Syndicate:**
   ```bash
   export LLM_PROVIDER=ollama
   # Or with specific model:
   export OLLAMA_MODEL=mistral
   python run.py
   ```

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Model name |
| `LLM_PROVIDER` | `auto` | Set to `ollama` to force Ollama-only |

### Recommended Models

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| `llama3.2` | 2GB | Fast | High | Default recommendation |
| `llama3.2:3b` | 2GB | Fastest | Good | Quick responses |
| `mistral` | 4GB | Medium | High | Detailed analysis |
| `phi3` | 2GB | Fast | Good | Lightweight option |
| `llama3.1:8b` | 5GB | Medium | Excellent | Best local quality |

### GPU Acceleration
Ollama automatically detects and uses your GPU. For NVIDIA:
```bash
# Check GPU is detected
ollama run llama3.2 --verbose
```

---

## 3. llama.cpp (Direct Local)

Direct llama.cpp integration for maximum control over local inference.

### Setup

1. **Install llama-cpp-python:**
   ```bash
   # CPU only
   pip install llama-cpp-python

   # NVIDIA GPU (CUDA 12.4)
   pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124

   # NVIDIA GPU (CUDA 12.1)
   pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121

   # macOS Metal (automatic)
   pip install llama-cpp-python
   ```

2. **Download a GGUF model:**
   ```bash
   # Using Syndicate's built-in downloader
   python scripts/local_llm.py --download mistral-7b

   # Or manually from HuggingFace
   # https://huggingface.co/TheBloke
   ```

3. **Configure:**
   ```bash
   export LOCAL_LLM_MODEL="./models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
   export PREFER_LOCAL_LLM=1  # Skip Gemini, use local directly
   python run.py
   ```

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LOCAL_LLM_MODEL` | (auto-detect) | Path to GGUF model file |
| `LOCAL_LLM_GPU_LAYERS` | `0` | GPU layers (`-1`=all, `0`=CPU) |
| `LOCAL_LLM_CONTEXT` | `4096` | Context window size |
| `LOCAL_LLM_THREADS` | `0` | CPU threads (`0`=auto) |
| `LOCAL_LLM_AUTO_DOWNLOAD` | `0` | Auto-download model if none found |
| `PREFER_LOCAL_LLM` | `0` | Use local as primary (skip Gemini) |

### GPU Configuration

```bash
# Full GPU offload (fastest, requires VRAM)
export LOCAL_LLM_GPU_LAYERS=-1

# Partial offload (balance CPU/GPU)
export LOCAL_LLM_GPU_LAYERS=20

# CPU only (safest, works everywhere)
export LOCAL_LLM_GPU_LAYERS=0
```

### VRAM Requirements

| Model Size | Q4_K_M | Q5_K_M | Q8_0 |
|------------|--------|--------|------|
| 7B | ~4.5 GB | ~5 GB | ~7 GB |
| 13B | ~8 GB | ~9 GB | ~13 GB |
| 70B | ~40 GB | ~45 GB | ~70 GB |

### Recommended Models

```bash
# Fast and capable (4.4 GB)
python scripts/local_llm.py --download mistral-7b

# Best quality/speed ratio (4.9 GB)
python scripts/local_llm.py --download llama3-8b

# Smallest, still good (2.2 GB)
python scripts/local_llm.py --download phi3-mini
```

### Model Search Paths
Syndicate searches these directories for `.gguf` files:
1. `./models/` (project directory)
2. `~/.cache/syndicate/models/`
3. `C:/models/` (Windows) or `/models/` (Linux/Mac)
4. Path specified in `LOCAL_LLM_MODEL`

---

## Provider Priority & Fallback

### Default Behavior
```
Gemini (cloud) → Ollama (local server) → llama.cpp (local file)
```

### Local-First Mode
```bash
export PREFER_LOCAL_LLM=1
# Order: llama.cpp → Ollama → Gemini
```

### Force Specific Provider
```bash
export LLM_PROVIDER=local   # Only llama.cpp, no cloud
export LLM_PROVIDER=ollama  # Only Ollama
export LLM_PROVIDER=gemini  # Only Gemini
```

### Automatic Fallback
When the primary provider fails (quota, error, timeout), Syndicate automatically switches to the next available provider:

```
[LLM] ✓ Primary: Gemini (models/gemini-pro-latest)
[LLM] ✓ Fallback ready: Ollama (llama3.2)
[LLM] ✓ Fallback ready: Local LLM (mistral-7b) [CPU]
...
[LLM] Gemini quota: Resource exhausted
[LLM] ⚡ Switching to Ollama (llama3.2): quota
[LLM] ✓ Ollama (llama3.2) activated - continuing without interruption
```

---

## Offline / Air-Gapped Usage

For environments without internet access:

1. **Pre-download model** (on a connected machine):
   ```bash
   python scripts/local_llm.py --download mistral-7b
   # Copy ~/.cache/syndicate/models/ to air-gapped machine
   ```

2. **Configure for offline use:**
   ```bash
   export LLM_PROVIDER=local
   export LOCAL_LLM_MODEL="/path/to/model.gguf"
   export LOCAL_LLM_GPU_LAYERS=-1  # Optional: GPU acceleration
   ```

3. **Run without network:**
   ```bash
   python run.py --no-notion  # Skip Notion sync too
   ```

---

## Troubleshooting

### "No LLM providers available"
```bash
# Check what's available
python -c "from scripts.local_llm import HAS_LLM_SUPPORT, HAS_OLLAMA, BACKEND; print(f'LLM: {HAS_LLM_SUPPORT}, Ollama: {HAS_OLLAMA}, Backend: {BACKEND}')"

# Install llama-cpp-python
pip install llama-cpp-python

# Or start Ollama
ollama serve
```

### "Model not found"
```bash
# List available models
python scripts/local_llm.py --list

# Download a model
python scripts/local_llm.py --download mistral-7b
```

### "CUDA out of memory"
```bash
# Reduce GPU layers
export LOCAL_LLM_GPU_LAYERS=10  # Try fewer layers

# Or use CPU only
export LOCAL_LLM_GPU_LAYERS=0
```

### "Ollama connection refused"
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama server
ollama serve
```

### Slow Generation
```bash
# Enable GPU (if available)
export LOCAL_LLM_GPU_LAYERS=-1

# Use smaller model
python scripts/local_llm.py --download phi3-mini

# For Ollama, use smaller variant
ollama pull llama3.2:3b
```

---

## Performance Tips

1. **GPU Acceleration**: Always use `-1` for `LOCAL_LLM_GPU_LAYERS` if you have sufficient VRAM
2. **Quantization**: Q4_K_M offers the best speed/quality tradeoff
3. **Context Size**: Reduce `LOCAL_LLM_CONTEXT` to 2048 for faster inference
4. **Model Size**: 7B models are usually sufficient for analysis tasks
5. **Ollama vs llama.cpp**: Ollama has better model caching; llama.cpp has more control

---

## Environment Variables Reference

### Provider Selection
| Variable | Values | Description |
|----------|--------|-------------|
| `LLM_PROVIDER` | `gemini`, `ollama`, `local`, `auto` | Force specific provider |
| `PREFER_LOCAL_LLM` | `1`, `true`, `yes` | Use local providers first |

### Gemini
| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | - | Google AI API key |
| `GEMINI_MODEL` | `models/gemini-pro-latest` | Model name |

### Ollama
| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Server URL |
| `OLLAMA_MODEL` | `llama3.2` | Model name |

### llama.cpp / Local
| Variable | Default | Description |
|----------|---------|-------------|
| `LOCAL_LLM_MODEL` | (auto-detect) | Path to GGUF file |
| `LOCAL_LLM_GPU_LAYERS` | `0` | GPU offload (-1=all) |
| `LOCAL_LLM_CONTEXT` | `4096` | Context window |
| `LOCAL_LLM_THREADS` | `0` | CPU threads (0=auto) |
| `LOCAL_LLM_AUTO_DOWNLOAD` | `0` | Auto-download model |

---

## API Compatibility

All providers implement the same `generate_content(prompt)` interface, returning a Gemini-compatible response:

```python
from scripts.local_llm import LocalLLM, OllamaLLM, GeminiCompatibleLLM

# All return response.text
llm = LocalLLM("model.gguf")
response = llm.generate_content("Analyze gold...")
print(response.text)

# Ollama
ollama = OllamaLLM(model="llama3.2")
response = ollama.generate_content("Analyze gold...")
print(response.text)
```

---

## Further Reading

- [Ollama Documentation](https://ollama.ai)
- [llama.cpp GitHub](https://github.com/ggerganov/llama.cpp)
- [GGUF Models on HuggingFace](https://huggingface.co/models?library=gguf)
- [Google AI Studio](https://aistudio.google.com)
