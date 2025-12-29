#!/usr/bin/env python3
"""
Syndicate Local LLM Provider

Provides a high-level Python interface for local LLM inference.
Supports multiple backends:
1. pyvdb (native C++ bindings from Vector Studio) - best performance
2. llama-cpp-python (pip installable) - easy setup

Usage:
    from scripts.local_llm import LocalLLM

    llm = LocalLLM()
    llm.load_model("models/mistral-7b-instruct-v0.3.Q4_K_M.gguf")

    response = llm.generate("Analyze gold price action today...")
    # or
    response = llm.chat([
        {"role": "system", "content": "You are a precious metals analyst."},
        {"role": "user", "content": "What is your gold bias today?"}
    ])
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================================
# Utilities
# ============================================================================


def get_env_int(key: str, default: int) -> int:
    """Get integer from environment variable."""
    val = os.environ.get(key, "")
    try:
        return int(val) if val else default
    except ValueError:
        return default


def get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean from environment variable."""
    val = os.environ.get(key, "").lower()
    if val in ("1", "true", "yes", "on"):
        return True
    if val in ("0", "false", "no", "off"):
        return False
    return default


def is_ollama_reachable(host: str, timeout_s: int = 2) -> bool:
    """Quick check whether an Ollama server is reachable.

    Returns True if a GET to /api/tags returns 200 within timeout.
    """
    try:
        import requests

        resp = requests.get(f"{host.rstrip('/')}/api/tags", timeout=timeout_s)
        return resp.status_code == 200
    except Exception:
        return False


# ============================================================================
# Backend Detection - Try multiple LLM backends
# ============================================================================

# Backend 1: Native pyvdb (C++ bindings from Vector Studio)
try:
    import pyvdb

    HAS_PYVDB = pyvdb.has_llm_support()
except ImportError:
    pyvdb = None
    HAS_PYVDB = False

# Backend 2: llama-cpp-python (pip install llama-cpp-python)
try:
    from llama_cpp import Llama

    HAS_LLAMA_CPP_PYTHON = True
except ImportError:
    Llama = None
    HAS_LLAMA_CPP_PYTHON = False

# Backend 3: Ollama (requires ollama server running)
try:
    import threading

    # Concurrency limit for Ollama (prevent overload). Default: 2 concurrent calls
    _OLLAMA_MAX_CONCURRENCY = int(os.environ.get("OLLAMA_MAX_CONCURRENCY", "2"))
    _ollama_semaphore = threading.BoundedSemaphore(_OLLAMA_MAX_CONCURRENCY)

    # Check if Ollama is explicitly disabled via env
    _ollama_disabled = get_env_bool("OLLAMA_DISABLE") or get_env_bool("DISABLE_OLLAMA")
    if _ollama_disabled:
        HAS_OLLAMA = False
    else:
        _ollama_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        ping_timeout = int(os.environ.get("OLLAMA_PING_TIMEOUT_S", "2"))
        HAS_OLLAMA = is_ollama_reachable(_ollama_url, timeout_s=ping_timeout)
except Exception:
    HAS_OLLAMA = False

# Determine best available backend for local models
# (Ollama is separate - it's a server-based provider)
if HAS_PYVDB:
    BACKEND = "pyvdb"
elif HAS_LLAMA_CPP_PYTHON:
    BACKEND = "llama-cpp-python"
else:
    BACKEND = None

HAS_LLM_SUPPORT = BACKEND is not None or HAS_OLLAMA
# Keep old name for backwards compatibility
HAS_NATIVE_LLM = HAS_LLM_SUPPORT

# ============================================================================
# Environment Variable Configuration
# ============================================================================
# LLM Provider Selection:
# LLM_PROVIDER         - Force provider: gemini, ollama, local (default: auto)
# PREFER_LOCAL_LLM     - Use local LLM first, skip Gemini (1/true)
#
# Local LLM (llama.cpp):
# LOCAL_LLM_MODEL      - Path to GGUF model file
# LOCAL_LLM_GPU_LAYERS - Number of layers to offload to GPU (0=CPU only, -1=all)
# LOCAL_LLM_CONTEXT    - Context window size (default: 4096)
# LOCAL_LLM_THREADS    - Number of CPU threads (0=auto)
# LOCAL_LLM_AUTO_DOWNLOAD - Auto-download recommended model if none found (1/true)
#
# Ollama:
# OLLAMA_HOST          - Ollama server URL (default: http://localhost:11434)
# OLLAMA_MODEL         - Ollama model name (default: llama3.2)


@dataclass
class LLMConfig:
    """Configuration for local LLM.

    All settings can be overridden via environment variables:
    - LOCAL_LLM_GPU_LAYERS: Number of layers to offload to GPU
      - 0 = CPU only (default, safe)
      - -1 = Offload all layers to GPU (fastest if you have VRAM)
      - N = Offload N layers (balance CPU/GPU)
    - LOCAL_LLM_CONTEXT: Context window size (default: 4096)
    - LOCAL_LLM_THREADS: CPU threads (0 = auto-detect)
    """

    model_path: str = ""
    n_ctx: int = field(default_factory=lambda: get_env_int("LOCAL_LLM_CONTEXT", 4096))
    n_batch: int = 512  # Batch size
    n_threads: int = field(default_factory=lambda: get_env_int("LOCAL_LLM_THREADS", 0))
    n_gpu_layers: int = field(default_factory=lambda: get_env_int("LOCAL_LLM_GPU_LAYERS", 0))
    use_mmap: bool = True
    use_mlock: bool = False


@dataclass
class GenerationConfig:
    """Generation parameters."""

    max_tokens: int = 1024
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    stop_sequences: List[str] = field(default_factory=list)
    stream: bool = False
    on_token: Optional[Callable[[str], bool]] = None


class LocalLLM:
    """
    Local LLM provider with multiple backend support.

    Backends (in priority order):
    1. pyvdb - Native C++ bindings (best performance)
    2. llama-cpp-python - Pure Python bindings (easy install)

    Drop-in replacement for Gemini API with similar interface.
    """

    def __init__(self, model_path: Optional[str] = None, config: Optional[LLMConfig] = None):
        """
        Initialize the local LLM.

        Args:
            model_path: Path to GGUF model file (optional, can load later)
            config: LLM configuration (optional)
        """
        self._engine = None
        self._llama = None  # For llama-cpp-python backend
        self._config = config or LLMConfig()
        self._loaded = False
        self._model_name = ""
        self._backend = BACKEND

        # Default model search paths
        self._model_dirs = [
            PROJECT_ROOT / "models",
            Path.home() / ".cache" / "syndicate" / "models",
            Path("C:/models"),
            Path("/models"),
            Path(os.environ.get("LOCAL_LLM_MODEL", "")).parent if os.environ.get("LOCAL_LLM_MODEL") else None,
        ]
        self._model_dirs = [d for d in self._model_dirs if d is not None]

        if model_path:
            self.load_model(model_path)
        elif os.environ.get("LOCAL_LLM_MODEL"):
            self.load_model(os.environ.get("LOCAL_LLM_MODEL"))
        elif get_env_bool("LOCAL_LLM_AUTO_DOWNLOAD"):
            # Auto-download a model if none found and auto-download is enabled
            self._try_auto_load()

    def _try_auto_load(self):
        """Try to find or auto-download a model."""
        models = self.find_models()
        if models:
            # Use the first found model
            print(f"[LLM] Found model: {models[0]['name']}")
            self.load_model(models[0]["path"])
        else:
            # Auto-download phi3-mini (smallest, still capable)
            print("[LLM] No models found, auto-downloading phi3-mini...")
            model_path = download_model("phi3-mini")
            if model_path:
                self.load_model(model_path)

    @property
    def is_available(self) -> bool:
        """Check if LLM support is available."""
        return HAS_LLM_SUPPORT

    @property
    def is_loaded(self) -> bool:
        """Check if a model is loaded."""
        if self._backend == "pyvdb":
            return self._loaded and self._engine is not None
        elif self._backend == "llama-cpp-python":
            return self._loaded and self._llama is not None
        return False

    @property
    def model_name(self) -> str:
        """Get the loaded model name."""
        return self._model_name

    @property
    def backend(self) -> str:
        """Get the active backend name."""
        return self._backend or "none"

    def find_models(self) -> List[Dict[str, Any]]:
        """
        Find all available GGUF models.

        Returns:
            List of model info dicts with path, name, size, quantization
        """
        models = []

        for model_dir in self._model_dirs:
            if not model_dir.exists():
                continue

            if HAS_PYVDB:
                paths = pyvdb.find_gguf_models(str(model_dir))
                for path in paths:
                    meta = pyvdb.read_gguf_metadata(path)
                    if meta:
                        models.append(
                            {
                                "path": str(path),
                                "name": meta.name,
                                "architecture": meta.architecture,
                                "quantization": meta.quantization,
                                "size_gb": meta.file_size / (1024**3),
                                "context_length": meta.context_length,
                            }
                        )
            else:
                # Fallback: just list .gguf files
                for gguf in model_dir.glob("*.gguf"):
                    models.append(
                        {
                            "path": str(gguf),
                            "name": gguf.stem,
                            "size_gb": gguf.stat().st_size / (1024**3),
                        }
                    )

        return models

    def load_model(self, model_path: str, config: Optional[LLMConfig] = None) -> bool:
        """
        Load a GGUF model.

        Args:
            model_path: Path to the GGUF model file
            config: Optional configuration override

        Returns:
            True if loaded successfully
        """
        if not HAS_LLM_SUPPORT:
            print("[LLM] No LLM backend available.")
            print("[LLM] Install with: pip install llama-cpp-python")
            print("[LLM] Or build Vector Studio with VDB_USE_LLAMA_CPP=ON")
            return False

        path = Path(model_path)
        if not path.exists():
            # Try model directories
            for model_dir in self._model_dirs:
                candidate = model_dir / model_path
                if candidate.exists():
                    path = candidate
                    break
            else:
                print(f"[LLM] Model not found: {model_path}")
                return False

        cfg = config or self._config
        print(f"[LLM] Loading model: {path.name} (backend: {self._backend})")

        # Backend 1: pyvdb (native C++)
        if self._backend == "pyvdb":
            self._engine = pyvdb.create_llm_engine()

            native_config = pyvdb.LLMConfig()
            native_config.model_path = str(path)
            native_config.n_ctx = cfg.n_ctx
            native_config.n_batch = cfg.n_batch
            native_config.n_threads = cfg.n_threads
            native_config.n_gpu_layers = cfg.n_gpu_layers
            native_config.use_mmap = cfg.use_mmap
            native_config.use_mlock = cfg.use_mlock

            if self._engine.load(native_config):
                self._loaded = True
                self._model_name = self._engine.model_name()
                print(f"[LLM] Model loaded: {self._model_name}")
                print(f"[LLM] Context: {self._engine.context_size()} tokens")
                return True
            else:
                print("[LLM] Failed to load model")
                self._engine = None
                return False

        # Backend 2: llama-cpp-python
        elif self._backend == "llama-cpp-python":
            try:
                n_threads = cfg.n_threads if cfg.n_threads > 0 else None
                self._llama = Llama(
                    model_path=str(path),
                    n_ctx=cfg.n_ctx,
                    n_batch=cfg.n_batch,
                    n_threads=n_threads,
                    n_gpu_layers=cfg.n_gpu_layers,
                    use_mmap=cfg.use_mmap,
                    use_mlock=cfg.use_mlock,
                    verbose=False,
                )
                self._loaded = True
                self._model_name = path.stem
                print(f"[LLM] Model loaded: {self._model_name}")
                print(f"[LLM] Context: {cfg.n_ctx} tokens")
                return True
            except Exception as e:
                print(f"[LLM] Failed to load model: {e}")
                self._llama = None
                return False

        return False

    def unload(self):
        """Unload the current model."""
        if self._engine:
            self._engine.unload()
            self._engine = None
        if self._llama:
            del self._llama
            self._llama = None
        self._loaded = False
        self._model_name = ""

    def generate(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        stop_sequences: Optional[List[str]] = None,
        **kwargs,
    ) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: The input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0 = greedy)
            top_p: Nucleus sampling threshold
            top_k: Top-k sampling
            stop_sequences: Sequences that stop generation

        Returns:
            Generated text
        """
        if not self.is_loaded:
            raise RuntimeError("No model loaded. Call load_model() first.")

        # Backend 1: pyvdb
        if self._backend == "pyvdb" and self._engine:
            params = pyvdb.GenerationParams()
            params.max_tokens = max_tokens
            params.temperature = temperature
            params.top_p = top_p
            params.top_k = top_k
            if stop_sequences:
                params.stop_sequences = stop_sequences
            return self._engine.generate(prompt, params)

        # Backend 2: llama-cpp-python
        elif self._backend == "llama-cpp-python" and self._llama:
            output = self._llama(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                stop=stop_sequences or [],
                echo=False,
            )
            return output["choices"][0]["text"]

        raise RuntimeError("No LLM backend available")

    def chat(
        self, messages: List[Dict[str, str]], max_tokens: int = 1024, temperature: float = 0.7, **kwargs
    ) -> Dict[str, Any]:
        """
        Chat completion with message history.

        Args:
            messages: List of {"role": "system/user/assistant", "content": "..."}
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Dict with 'content', 'tokens_generated', 'generation_time_ms'
        """
        if not self.is_loaded:
            raise RuntimeError("No model loaded. Call load_model() first.")

        # Backend 1: pyvdb
        if self._backend == "pyvdb" and self._engine:
            native_messages = []
            for msg in messages:
                role_str = msg.get("role", "user").lower()
                if role_str == "system":
                    role = pyvdb.Role.System
                elif role_str == "assistant":
                    role = pyvdb.Role.Assistant
                else:
                    role = pyvdb.Role.User
                native_messages.append(pyvdb.Message(role, msg.get("content", "")))

            params = pyvdb.GenerationParams()
            params.max_tokens = max_tokens
            params.temperature = temperature

            result = self._engine.chat(native_messages, params)

            return {
                "content": result.content,
                "tokens_generated": result.tokens_generated,
                "tokens_prompt": result.tokens_prompt,
                "generation_time_ms": result.generation_time_ms,
            }

        # Backend 2: llama-cpp-python
        elif self._backend == "llama-cpp-python" and self._llama:
            import time

            start = time.time()
            output = self._llama.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            elapsed = (time.time() - start) * 1000

            content = output["choices"][0]["message"]["content"]
            return {
                "content": content,
                "tokens_generated": output.get("usage", {}).get("completion_tokens", 0),
                "tokens_prompt": output.get("usage", {}).get("prompt_tokens", 0),
                "generation_time_ms": elapsed,
            }

        raise RuntimeError("No LLM backend available")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if not self.is_loaded:
            return len(text.split())  # Rough estimate

        if self._backend == "pyvdb" and self._engine:
            return self._engine.count_tokens(text)
        elif self._backend == "llama-cpp-python" and self._llama:
            return len(self._llama.tokenize(text.encode()))

        return len(text.split())


class GeminiCompatibleLLM:
    """
    Wrapper that provides Gemini-compatible API for seamless drop-in replacement.

    Usage:
        # Instead of:
        # model = genai.GenerativeModel('gemini-pro')
        # response = model.generate_content(prompt)

        # Use:
        model = GeminiCompatibleLLM("mistral-7b-instruct.gguf")
        response = model.generate_content(prompt)
        print(response.text)
    """

    def __init__(self, model_path: str, **config):
        self._llm = LocalLLM(model_path, LLMConfig(**config) if config else None)

    def _wrap_prompt(self, prompt: str) -> str:
        """Wrap prompt in instruct template if needed."""
        # Detect model type from path or loaded model name
        model_name = self._llm.model_name.lower()

        # If already wrapped, don't re-wrap
        if "<|user|>" in prompt or "[INST]" in prompt or "<|start_header_id|>" in prompt:
            return prompt

        if "phi-3" in model_name or "phi3" in model_name:
            return f"<|user|>\n{prompt}<|end|>\n<|assistant|>"
        elif "llama-3" in model_name or "llama3" in model_name:
            return f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
        elif "mistral" in model_name or "mixtral" in model_name:
            return f"[INST] {prompt} [/INST]"
        else:
            # Default to basic instruct if unknown but common and has 'instruct' in name
            if "instruct" in model_name:
                return f"<|user|>\n{prompt}<|end|>\n<|assistant|>"

        return prompt

    def generate_content(self, prompt: str, **kwargs) -> "GenerateContentResponse":
        """
        Generate content (Gemini-compatible API).

        Args:
            prompt: The input prompt

        Returns:
            Response object with .text attribute
        """
        wrapped_prompt = self._wrap_prompt(prompt)
        text = self._llm.generate(wrapped_prompt, **kwargs)
        return GenerateContentResponse(text)


class GenerateContentResponse:
    """Gemini-compatible response object."""

    def __init__(self, text: str):
        self.text = text
        self.candidates = [{"content": {"parts": [{"text": text}]}}]


# ============================================================================
# Ollama Provider
# ============================================================================


class OllamaLLM:
    """
    Ollama LLM provider - connects to local Ollama server.

    Ollama provides easy model management and GPU acceleration.
    Install: https://ollama.ai

    Usage:
        # Start Ollama server first: ollama serve
        # Pull a model: ollama pull llama3.2

        llm = OllamaLLM()
        response = llm.generate("What is the gold price outlook?")
        # or chat:
        response = llm.chat([{"role": "user", "content": "Hello!"}])

    Environment Variables:
        OLLAMA_HOST  - Server URL (default: http://localhost:11434)
        OLLAMA_MODEL - Model name (default: llama3.2)
    """

    def __init__(self, model: str = None, host: str = None):
        """
        Initialize Ollama client.

        Args:
            model: Model name (e.g., "llama3.2", "mistral", "phi3")
            host: Ollama server URL
        """
        self._host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self._model = model or os.environ.get("OLLAMA_MODEL", "llama3.2")
        self._available = False
        self._loaded_model = None

        # Respect explicit disable flag
        if get_env_bool("OLLAMA_DISABLE") or get_env_bool("DISABLE_OLLAMA"):
            print("[Ollama] Disabled via environment (OLLAMA_DISABLE).")
            self._available = False
            return

        # Quick ping check to avoid long retries when host is down
        ping_timeout = int(os.environ.get("OLLAMA_PING_TIMEOUT_S", "2"))
        if not is_ollama_reachable(self._host, timeout_s=ping_timeout):
            print(
                f"[Ollama] Host not reachable at {self._host} (ping timeout {ping_timeout}s). Skipping Ollama provider."
            )
            self._available = False
            return

        # Host appears reachable; perform a short listing to get installed models
        try:
            import requests

            list_timeout = int(os.environ.get("OLLAMA_LIST_TIMEOUT_S", "5"))
            resp = requests.get(f"{self._host}/api/tags", timeout=list_timeout)
            if resp.status_code == 200:
                self._available = True
                models = resp.json().get("models", [])
                self._installed_models = [m["name"] for m in models]
                # Check if requested model is available
                if any(self._model in m for m in self._installed_models):
                    self._loaded_model = self._model
        except Exception as e:
            print(f"[Ollama] Listing models failed: {e}")
            self._available = False

    @property
    def is_available(self) -> bool:
        """Check if Ollama server is accessible."""
        return self._available

    @property
    def is_loaded(self) -> bool:
        """Check if model is available."""
        return self._loaded_model is not None

    @property
    def model_name(self) -> str:
        """Get loaded model name."""
        return self._loaded_model or self._model

    def list_models(self) -> List[str]:
        """List installed Ollama models."""
        return getattr(self, "_installed_models", [])

    def pull_model(self, model: str) -> bool:
        """Pull a model from Ollama library."""
        try:
            import requests

            print(f"[Ollama] Pulling {model}...")
            resp = requests.post(f"{self._host}/api/pull", json={"name": model}, stream=True, timeout=600)
            for line in resp.iter_lines():
                if line:
                    import json

                    data = json.loads(line)
                    if "status" in data:
                        print(f"\r[Ollama] {data['status']}", end="", flush=True)
            print()
            self._loaded_model = model
            return True
        except Exception as e:
            print(f"[Ollama] Pull failed: {e}")
            return False

    def generate(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """
        Generate text completion.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        if not self._available:
            raise RuntimeError("Ollama server not available")

        # Avoid overloading Ollama: try to acquire semaphore, fail fast if overloaded
        acquired = False
        try:
            acquired = _ollama_semaphore.acquire(blocking=False)
            if not acquired:
                raise RuntimeError("Ollama overloaded: concurrency limit reached")

            import requests

            timeout = int(os.environ.get("OLLAMA_TIMEOUT_S", "600"))
            resp = requests.post(
                f"{self._host}/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                    },
                    "stream": False,
                },
                timeout=timeout,
            )
            resp.raise_for_status()
            return resp.json()["response"]
        except Exception as e:
            raise RuntimeError(f"Ollama generate failed: {e}")
        finally:
            if acquired:
                _ollama_semaphore.release()

    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Chat completion with message history.

        Args:
            messages: List of {"role": "user/assistant/system", "content": "..."}
            max_tokens: Maximum tokens
            temperature: Sampling temperature

        Returns:
            Dict with 'content' and token info
        """
        if not self._available:
            raise RuntimeError("Ollama server not available")

        # Avoid overloading Ollama: try to acquire semaphore, fail fast if overloaded
        acquired = False
        try:
            acquired = _ollama_semaphore.acquire(blocking=False)
            if not acquired:
                raise RuntimeError("Ollama overloaded: concurrency limit reached")

            import time

            import requests

            start = time.time()
            timeout = int(os.environ.get("OLLAMA_TIMEOUT_S", "600"))
            resp = requests.post(
                f"{self._host}/api/chat",
                json={
                    "model": self._model,
                    "messages": messages,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                    },
                    "stream": False,
                },
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            elapsed = (time.time() - start) * 1000

            return {
                "content": data["message"]["content"],
                "tokens_generated": data.get("eval_count", 0),
                "tokens_prompt": data.get("prompt_eval_count", 0),
                "generation_time_ms": elapsed,
            }
        except Exception as e:
            raise RuntimeError(f"Ollama chat failed: {e}")
        finally:
            if acquired:
                _ollama_semaphore.release()

    def generate_content(self, prompt: str, **kwargs) -> "GenerateContentResponse":
        """
        Gemini-compatible API.

        Args:
            prompt: Input prompt

        Returns:
            GenerateContentResponse with .text attribute
        """
        text = self.generate(prompt, **kwargs)
        return GenerateContentResponse(text)


# ============================================================================
# Auto-download popular models
# ============================================================================

RECOMMENDED_MODELS = {
    "mistral-7b": {
        "url": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        "filename": "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        "size_gb": 4.4,
        "description": "Fast, excellent for structured output",
    },
    "llama3-8b": {
        "url": "https://huggingface.co/QuantFactory/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct.Q4_K_M.gguf",
        "filename": "Meta-Llama-3.1-8B-Instruct.Q4_K_M.gguf",
        "size_gb": 4.9,
        "description": "Best quality/speed ratio",
    },
    "phi3-mini": {
        "url": "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf",
        "filename": "Phi-3-mini-4k-instruct-q4.gguf",
        "size_gb": 2.2,
        "description": "Smallest, still capable",
    },
}


def download_model(model_key: str, dest_dir: Optional[str] = None) -> Optional[str]:
    """
    Download a recommended model with progress bar and resume support.

    Args:
        model_key: Key from RECOMMENDED_MODELS (e.g., 'mistral-7b')
        dest_dir: Destination directory (default: ~/.cache/syndicate/models)

    Returns:
        Path to downloaded model, or None if failed
    """
    if model_key not in RECOMMENDED_MODELS:
        print(f"Unknown model: {model_key}")
        print(f"Available: {', '.join(RECOMMENDED_MODELS.keys())}")
        return None

    model_info = RECOMMENDED_MODELS[model_key]

    dest_path = Path(dest_dir) if dest_dir else Path.home() / ".cache" / "syndicate" / "models"
    dest_path.mkdir(parents=True, exist_ok=True)

    filepath = dest_path / model_info["filename"]
    expected_size = int(model_info["size_gb"] * 1024 * 1024 * 1024)  # Convert to bytes

    # Check if complete file exists
    if filepath.exists():
        current_size = filepath.stat().st_size
        # Allow 5% tolerance for size check
        if current_size >= expected_size * 0.95:
            print(f"[LLM] Model already exists: {filepath}")
            return str(filepath)
        else:
            print(
                f"[LLM] Incomplete download detected ({current_size / 1024**3:.2f} GB / {model_info['size_gb']:.1f} GB)"
            )
            print("[LLM] Resuming download...")

    print(f"[LLM] Downloading {model_key} ({model_info['size_gb']:.1f} GB)...")
    print(f"[LLM] {model_info['description']}")
    print(f"[LLM] Destination: {filepath}")

    try:
        import requests
        from tqdm import tqdm

        # Get file size and check for resume support
        head_response = requests.head(model_info["url"], allow_redirects=True, timeout=30)
        total_size = int(head_response.headers.get("content-length", 0))
        accept_ranges = head_response.headers.get("accept-ranges", "none")

        # Check existing file for resume
        resume_pos = 0
        mode = "wb"
        if filepath.exists() and accept_ranges == "bytes":
            resume_pos = filepath.stat().st_size
            if resume_pos < total_size:
                mode = "ab"
                print(f"[LLM] Resuming from {resume_pos / 1024**3:.2f} GB")

        # Download with progress bar
        headers = {}
        if resume_pos > 0 and mode == "ab":
            headers["Range"] = f"bytes={resume_pos}-"

        response = requests.get(model_info["url"], headers=headers, stream=True, timeout=30)
        response.raise_for_status()

        # Progress bar
        with open(filepath, mode) as f:
            with tqdm(
                total=total_size,
                initial=resume_pos,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=model_key,
                ncols=80,
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

        # Verify download
        final_size = filepath.stat().st_size
        if final_size >= total_size * 0.99:  # Allow 1% tolerance
            print(f"\n[LLM] Download complete: {filepath}")
            return str(filepath)
        else:
            print(
                f"\n[LLM] WARNING: Download may be incomplete ({final_size / 1024**3:.2f} GB / {total_size / 1024**3:.2f} GB)"
            )
            return str(filepath)

    except ImportError:
        # Fallback without tqdm
        print("[LLM] Note: Install 'tqdm' for progress bars")
        try:
            import urllib.request

            def progress_hook(count, block_size, total_size):
                percent = int(count * block_size * 100 / total_size) if total_size > 0 else 0
                downloaded = count * block_size / (1024**3)
                print(f"\r[LLM] Downloading: {percent}% ({downloaded:.2f} GB)", end="", flush=True)

            urllib.request.urlretrieve(model_info["url"], filepath, progress_hook)
            print(f"\n[LLM] Downloaded: {filepath}")
            return str(filepath)
        except Exception as e:
            print(f"\n[LLM] Download failed: {e}")
            return None

    except Exception as e:
        print(f"\n[LLM] Download failed: {e}")
        if filepath.exists():
            size = filepath.stat().st_size / (1024**3)
            print(f"[LLM] Partial file saved ({size:.2f} GB). Re-run to resume.")
        return None


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Syndicate Local LLM")
    parser.add_argument("--list", action="store_true", help="List available models")
    parser.add_argument("--download", type=str, help="Download a model (mistral-7b, llama3-8b, phi3-mini)")
    parser.add_argument("--model", type=str, help="Path to GGUF model")
    parser.add_argument("--prompt", type=str, help="Generate from prompt")
    parser.add_argument("--interactive", action="store_true", help="Interactive chat mode")
    args = parser.parse_args()

    if args.list:
        print("\n=== Available Models ===")
        llm = LocalLLM()
        models = llm.find_models()
        if models:
            for m in models:
                print(f"  {m['name']}: {m.get('size_gb', 0):.1f} GB - {m['path']}")
        else:
            print("  No models found.")

        print("\n=== Recommended Downloads ===")
        for key, info in RECOMMENDED_MODELS.items():
            print(f"  {key}: {info['description']} ({info['size_gb']:.1f} GB)")
        print("\n  Download with: python local_llm.py --download mistral-7b")

    elif args.download:
        download_model(args.download)

    elif args.model and args.prompt:
        llm = LocalLLM(args.model)
        if llm.is_loaded:
            print(llm.generate(args.prompt))

    elif args.model and args.interactive:
        llm = LocalLLM(args.model)
        if llm.is_loaded:
            print(f"\nChat with {llm.model_name} (type 'quit' to exit)\n")
            messages = []
            while True:
                user_input = input("You: ").strip()
                if user_input.lower() in ("quit", "exit", "q"):
                    break

                messages.append({"role": "user", "content": user_input})
                result = llm.chat(messages)
                print(f"\nAssistant: {result['content']}\n")
                messages.append({"role": "assistant", "content": result["content"]})

    else:
        parser.print_help()
