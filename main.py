#!/opt/python3.12/bin/python3.12
# ══════════════════════════════════════════════════════════════════════════════
#  _________._____________.___ ____ ___  _________      .__         .__
# /   _____/|   \______   \   |    |   \/   _____/____  |  | ______ |  |__ _____
# \_____  \ |   ||       _/   |    |   /\_____  \__  \ |  | \____ \|  |  \__  \
# /        \|   ||    |   \   |    |  / /        \/ __ \|  |_|  |_> >   Y  \/ __ \_
# /_______  /|___||____|_  /___|______/ /_______  (____  /____/   __/|___|  (____  /
#         \/             \/                     \/     \/     |__|        \/     \/
#
# Syndicate - Precious Metals Intelligence System
# Copyright (c) 2025 SIRIUS Alpha
# All rights reserved.
# ══════════════════════════════════════════════════════════════════════════════
import argparse
import datetime
import json
import logging
import os
import re
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List, Optional, Tuple

import filelock
import pandas as pd
import schedule
from dotenv import load_dotenv

try:
    import pandas_ta as ta
except Exception:
    # dependencies (like numba) are unavailable; provide a lightweight fallback TA
    import pandas as _pd

    class _FallbackTA:
        @staticmethod
        def sma(series, length=50):
            return series.rolling(window=length).mean()

        @staticmethod
        def rsi(series, length=14):
            delta = series.diff()
            up = delta.clip(lower=0)
            down = -delta.clip(upper=0)
            ma_up = up.rolling(window=length, min_periods=length).mean()
            ma_down = down.rolling(window=length, min_periods=length).mean()
            rs = ma_up / ma_down
            return 100 - (100 / (1 + rs))

        @staticmethod
        def atr(high, low, close, length=14):
            prev_close = close.shift(1)
            tr1 = high - low
            tr2 = (high - prev_close).abs()
            tr3 = (low - prev_close).abs()
            tr = _pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            return tr.rolling(window=length, min_periods=length).mean()

        @staticmethod
        def adx(high, low, close, length=14):
            # Basic ADX implementation compatible with pandas Series input (fallback).
            try:
                prev_close = close.shift(1)
                tr1 = high - low
                tr2 = (high - prev_close).abs()
                tr3 = (low - prev_close).abs()
                tr = _pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                atr = tr.rolling(window=length, min_periods=length).mean()

                up_move = high.diff()
                down_move = -low.diff()
                # Use where to avoid setting dtype incompatible warnings
                plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
                minus_dm = (-down_move).where((down_move > up_move) & (down_move > 0), 0.0)

                plus_di = (plus_dm.rolling(window=length, min_periods=length).sum() / atr) * 100
                minus_di = (minus_dm.rolling(window=length, min_periods=length).sum() / atr) * 100

                dx = (plus_di - minus_di).abs() / (plus_di + minus_di) * 100
                adx = dx.rolling(window=length, min_periods=length).mean()

                df = _pd.concat(
                    [adx.rename(f"ADX_{length}"), plus_di.rename(f"DMP_{length}"), minus_di.rename(f"DMN_{length}")],
                    axis=1,
                )
                return df
            except Exception:
                return None

    ta = _FallbackTA()

    ta = _FallbackTA()
# Optional runtime hooks (deferred imports)
# `genai` (Google GenAI) and `mpf` (mplfinance) are imported lazily
# to avoid heavy startup latency during dry-runs or when providers are unused.
genai = None
mpf = None
import yfinance as yf

# Compatibility: ensure yf.download exists for test monkeypatches and legacy callers
if yf is not None and not hasattr(yf, "download"):

    def _yf_download(ticker, *args, **kwargs):
        t = yf.Ticker(ticker)
        return t.history(*args, **kwargs)

    yf.download = _yf_download
from colorama import init

# ==========================================
# LLM PROVIDER ABSTRACTION
# ==========================================

# Load .env early so credentials in the repo are available for provider init
try:
    try:
        from syndicate.utils.env_loader import load_env

        load_env()
    except Exception:
        load_dotenv()
except Exception:
    pass

# Helper for robust integer env parsing used across the module
try:
    # Prefer local helper if provided by `scripts/local_llm.py`
    from scripts.local_llm import get_env_int as _get_env_int  # type: ignore
except Exception:

    def _get_env_int(key: str, default: int) -> int:
        v = os.environ.get(key, "")
        try:
            return int(v) if v else default
        except Exception:
            import re

            m = re.match(r"\s*([+-]?\d+)", v or "")
            return int(m.group(1)) if m else default


class LLMProvider:
    """Abstract interface for LLM providers (Gemini, Local, etc.)"""

    def generate_content(self, prompt: str) -> Any:
        raise NotImplementedError


class GeminiProvider(LLMProvider):
    """Google Gemini API provider."""

    def __init__(self, model_name: str = "models/gemini-pro-latest"):
        # Import the Google GenAI client only when the provider is instantiated.
        # Try the legacy `google.generativeai` package first, then the compat shim.
        try:
            import google.generativeai as genai_mod  # type: ignore

            self._genai = genai_mod
            self.model = genai_mod.GenerativeModel(model_name)
            self.name = "Gemini"
        except Exception:
            try:
                from scripts import genai_compat as genai_compat  # type: ignore

                # Configure compat shim if an API key is present
                api_key = os.getenv("GEMINI_API_KEY")
                try:
                    if api_key:
                        genai_compat.configure(api_key=api_key)
                except Exception:
                    pass

                self._genai = genai_compat
                self.model = genai_compat.GenerativeModel(model_name)
                self.name = "Gemini"
            except Exception:
                raise RuntimeError(
                    "Gemini provider not available: google.generativeai package or compat shim not installed/configured"
                )

    def generate_content(self, prompt: str) -> Any:
        return self.model.generate_content(prompt)


class OllamaProvider(LLMProvider):
    """Ollama API provider - connects to local Ollama server.

    Ollama provides easy local model management with GPU acceleration.
    Install from: https://ollama.ai

    Configure via environment variables:
    - OLLAMA_HOST: Server URL (default: http://localhost:11434)
    - OLLAMA_MODEL: Model name (default: llama3.2)
    """

    def __init__(self, model: str = None):
        self.name = "Ollama"
        self._llm = None
        self._available = False

        try:
            from scripts.local_llm import OllamaLLM

            self._llm = OllamaLLM(model=model)
            self._available = self._llm.is_available
            if self._available:
                self.name = f"Ollama ({self._llm.model_name})"
        except ImportError as e:
            print(f"[Ollama] Not available: {e}")

    @property
    def is_available(self) -> bool:
        return self._available

    def generate_content(self, prompt: str) -> Any:
        if not self._available:
            raise RuntimeError("Ollama not available")
        return self._llm.generate_content(prompt)


class LocalLLMProvider(LLMProvider):
    """Local LLM provider using llama-cpp-python.

    Supports both CPU and GPU inference. Configure via environment variables:
    - LOCAL_LLM_MODEL: Path to GGUF model
    - LOCAL_LLM_GPU_LAYERS: GPU offload (0=CPU, -1=all layers to GPU)
    - LOCAL_LLM_CONTEXT: Context window size
    - LOCAL_LLM_AUTO_DOWNLOAD: Auto-download model if none found
    """

    def __init__(self, model_path: str = None, auto_find: bool = True):
        self.name = "Local"
        self._llm = None
        self._available = False

        try:
            from scripts.local_llm import GeminiCompatibleLLM, LLMConfig, LocalLLM, get_env_int

            # Build config from environment
            config = LLMConfig(
                n_gpu_layers=get_env_int("LOCAL_LLM_GPU_LAYERS", 0),
                n_ctx=get_env_int("LOCAL_LLM_CONTEXT", 4096),
                n_threads=get_env_int("LOCAL_LLM_THREADS", 0),
            )

            if model_path:
                # Filter out model_path from config to avoid multiple values error
                llm_params = {k: v for k, v in vars(config).items() if k != "model_path"}
                self._llm = GeminiCompatibleLLM(model_path, **llm_params)
                self._available = self._llm._llm.is_loaded
                if self._available:
                    gpu_info = f"GPU layers: {config.n_gpu_layers}" if config.n_gpu_layers else "CPU only"
                    print(f"[LLM] Local model loaded ({gpu_info})")
            elif auto_find:
                # Try to find a model or auto-download
                llm = LocalLLM(config=config)
                if llm.is_loaded:
                    self._llm = GeminiCompatibleLLM.__new__(GeminiCompatibleLLM)
                    self._llm._llm = llm
                    self._available = True
                else:
                    models = llm.find_models()
                    if models:
                        self._llm = GeminiCompatibleLLM(models[0]["path"], **vars(config))
                        self._available = self._llm._llm.is_loaded
        except ImportError as e:
            print(f"[LLM] Local LLM not available: {e}")
            pass

    @property
    def is_available(self) -> bool:
        return self._available

    def generate_content(self, prompt: str) -> Any:
        if not self._available:
            raise RuntimeError("Local LLM not available")
        return self._llm.generate_content(prompt)


class FallbackLLMProvider(LLMProvider):
    """
    Robust LLM provider with automatic fallback chain.

    Default Fallback Order (configurable via LLM_PROVIDER env var):
    1. Gemini API (cloud, high quality)
    2. Ollama (local server, easy model management)
    3. Local LLM / llama.cpp (on-device, no dependencies)

    Set PREFER_LOCAL_LLM=1 to reverse order (local first, no cloud).
    Set LLM_PROVIDER=ollama|local|gemini to force a specific provider.

    Switches to next provider after just 1 failure for fast recovery.
    """

    def __init__(self, config: "Config", logger: logging.Logger):
        self.name = "Fallback"
        self.config = config
        self.logger = logger
        self._gemini = None
        self._ollama = None
        self._local = None
        self._current = None
        self._providers = []  # Ordered list of available providers
        self._primary_failures = 0
        self._max_failures = 1  # Switch to next after 1 failure
        self._switched = False

        # Determine provider priority
        prefer_local = config.PREFER_LOCAL_LLM
        forced_provider = os.environ.get("LLM_PROVIDER", "").lower()

        # Build provider chain based on configuration
        if forced_provider == "local":
            self._init_local_only(config, logger)
        elif forced_provider == "ollama":
            self._init_ollama_only(config, logger)
        elif forced_provider == "gemini":
            self._init_gemini_only(config, logger)
        elif prefer_local:
            self._init_local_first(config, logger)
        else:
            self._init_gemini_first(config, logger)

        if not self._current:
            logger.warning("[LLM] ⚠ No LLM providers available! AI features disabled.")

    def _init_gemini_first(self, config, logger):
        """Default: Gemini → Ollama → Local"""
        # 1. Gemini (primary)
        if config.GEMINI_API_KEY:
            # Ensure config value takes precedence, but don't fail startup if assignment fails
            try:
                os.environ["GEMINI_API_KEY"] = config.GEMINI_API_KEY
            except Exception:
                pass

            # Remove competing environment keys that could cause library auto-selection
            os.environ.pop("GOOGLE_API_KEY", None)

            try:
                # Import the official client or compat shim into module globals
                if globals().get("genai") is None:
                    try:
                        import google.generativeai as genai_mod  # type: ignore

                        globals()["genai"] = genai_mod
                    except Exception:
                        try:
                            from scripts import genai_compat as genai_compat  # type: ignore

                            globals()["genai"] = genai_compat
                        except Exception:
                            # Neither client importable — propagate to fallback handling
                            raise

                # Configure the client and instantiate provider
                globals()["genai"].configure(api_key=config.GEMINI_API_KEY)
                self._gemini = GeminiProvider(config.GEMINI_MODEL)
                self._providers.append(self._gemini)
                self._current = self._gemini
                self.name = "Gemini"
                logger.info(f"[LLM] ✓ Primary: Gemini ({config.GEMINI_MODEL})")
            except Exception as e:
                logger.warning(f"[LLM] ✗ Gemini init failed: {e}")
                # If strict-gemini mode enabled, do not fallback
                if os.environ.get("LLM_STRICT_GEMINI", "0") == "1":
                    logger.error(
                        "[LLM] STRICT GEMINI MODE: aborting due to Gemini init failure and no fallbacks allowed"
                    )
                    raise
        # 2. Ollama (fallback 1)
        self._try_init_ollama(config, logger)

        # 3. Local LLM (fallback 2)
        self._try_init_local(config, logger)

        self._update_name()

    def _init_local_first(self, config, logger):
        """PREFER_LOCAL_LLM=1: Local → Ollama → Gemini"""
        logger.info("[LLM] Local-first mode enabled (PREFER_LOCAL_LLM=1)")

        # 1. Local LLM (primary)
        self._try_init_local(config, logger, as_primary=True)

        # 2. Ollama (fallback 1)
        self._try_init_ollama(config, logger)

        # 3. Gemini (fallback 2 - only if local fails)
        if config.GEMINI_API_KEY and not self._current:
            try:
                genai.configure(api_key=config.GEMINI_API_KEY)
                self._gemini = GeminiProvider(config.GEMINI_MODEL)
                self._providers.append(self._gemini)
                if not self._current:
                    self._current = self._gemini
                logger.info(f"[LLM] ✓ Fallback: Gemini ({config.GEMINI_MODEL})")
            except Exception as e:
                logger.debug(f"[LLM] Gemini fallback not available: {e}")

        self._update_name()

    def _init_local_only(self, config, logger):
        """LLM_PROVIDER=local: Only local LLM, no cloud"""
        logger.info("[LLM] Local-only mode (LLM_PROVIDER=local)")
        self._try_init_local(config, logger, as_primary=True)
        if not self._current:
            logger.warning("[LLM] ✗ No local model found. Set LOCAL_LLM_MODEL or install llama-cpp-python")
        self._update_name()

    def _init_ollama_only(self, config, logger):
        """LLM_PROVIDER=ollama: Only Ollama, no fallback"""
        logger.info("[LLM] Ollama-only mode (LLM_PROVIDER=ollama)")
        self._try_init_ollama(config, logger, as_primary=True)
        if not self._current:
            logger.warning("[LLM] ✗ Ollama not available. Run: ollama serve")
        self._update_name()

    def _init_gemini_only(self, config, logger):
        """LLM_PROVIDER=gemini: Only Gemini, no fallback"""
        logger.info("[LLM] Gemini-only mode (LLM_PROVIDER=gemini)")
        if config.GEMINI_API_KEY:
            try:
                genai.configure(api_key=config.GEMINI_API_KEY)
                self._gemini = GeminiProvider(config.GEMINI_MODEL)
                self._providers.append(self._gemini)
                self._current = self._gemini
                logger.info(f"[LLM] ✓ Gemini ({config.GEMINI_MODEL})")
            except Exception as e:
                logger.error(f"[LLM] ✗ Gemini init failed: {e}")
        else:
            logger.error("[LLM] ✗ GEMINI_API_KEY not set")
        self._update_name()

    def _try_init_ollama(self, config, logger, as_primary=False):
        """Try to initialize Ollama provider."""
        try:
            ollama_model = os.environ.get("OLLAMA_MODEL", "")
            self._ollama = OllamaProvider(model=ollama_model if ollama_model else None)
            if self._ollama.is_available:
                self._providers.append(self._ollama)
                if as_primary or not self._current:
                    self._current = self._ollama
                    logger.info(f"[LLM] ✓ {'Primary' if as_primary else 'Using'}: {self._ollama.name}")
                else:
                    logger.info(f"[LLM] ✓ Fallback ready: {self._ollama.name}")
            else:
                self._ollama = None
        except Exception as e:
            logger.debug(f"[LLM] Ollama not available: {e}")
            self._ollama = None

    def _try_init_local(self, config, logger, as_primary=False):
        """Try to initialize local LLM provider."""
        try:
            self._local = LocalLLMProvider(
                model_path=config.LOCAL_LLM_MODEL if config.LOCAL_LLM_MODEL else None, auto_find=True
            )
            if self._local.is_available:
                self._providers.append(self._local)
                gpu_layers = config.LOCAL_LLM_GPU_LAYERS
                gpu_mode = f"GPU ({gpu_layers} layers)" if gpu_layers else "CPU"
                model_name = config.LOCAL_LLM_MODEL.split("/")[-1] if config.LOCAL_LLM_MODEL else "auto-detected"

                if as_primary or not self._current:
                    self._current = self._local
                    logger.info(
                        f"[LLM] ✓ {'Primary' if as_primary else 'Using'}: Local LLM ({model_name}) [{gpu_mode}]"
                    )
                else:
                    logger.info(f"[LLM] ✓ Fallback ready: Local LLM ({model_name}) [{gpu_mode}]")
            else:
                self._local = None
                if as_primary:
                    logger.warning("[LLM] ✗ No local model found. Set LOCAL_LLM_MODEL or LOCAL_LLM_AUTO_DOWNLOAD=1")
        except Exception as e:
            logger.debug(f"[LLM] Local LLM not available: {e}")
            self._local = None

    def _update_name(self):
        """Update provider name based on chain."""
        if self._current:
            names = [p.name.split()[0] for p in self._providers]
            if len(names) > 1:
                self.name = f"{names[0]}+{'→'.join(names[1:])}"
            else:
                self.name = names[0] if names else "Unknown"

    @property
    def is_available(self) -> bool:
        return self._current is not None

    def _is_quota_error(self, error: Exception) -> bool:
        """Check if error is a quota/rate limit error."""
        error_str = str(error).lower()
        quota_patterns = [
            "quota",
            "rate limit",
            "429",
            "resource exhausted",
            "too many requests",
            "capacity",
            "overloaded",
        ]
        return any(p in error_str for p in quota_patterns)

    def _switch_to_next(self, reason: str) -> bool:
        """Switch to next available provider in the chain."""
        current_idx = self._providers.index(self._current) if self._current in self._providers else -1
        for i in range(current_idx + 1, len(self._providers)):
            next_provider = self._providers[i]
            if next_provider.is_available:
                self._current = next_provider
                self.name = f"{next_provider.name} (fallback)"
                self._switched = True
                self.logger.warning(f"[LLM] ⚡ Switching to {next_provider.name}: {reason[:60]}")
                self.logger.info(f"[LLM] ✓ {next_provider.name} activated - continuing without interruption")
                return True
        self.logger.error("[LLM] ✗ No more fallback providers available")
        return False

    def generate_content(self, prompt: str) -> Any:
        """
        Generate content with automatic fallback through provider chain.

        Switches to next provider after 1 failure for:
        - Quota exhaustion (429 errors)
        - Rate limiting
        - API unavailability
        - Any other transient errors

        Returns a Gemini-compatible response object.
        """
        if not self._current:
            raise RuntimeError("No LLM provider available")

        # Lightweight caching: check DB cache for identical prompt
        try:
            from db_manager import get_db

            db = get_db()
            import hashlib

            prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            cache_entry = db.get_llm_cache(prompt_hash)
            if cache_entry and cache_entry.get("last_used"):
                # If entry exists, return cached response (best-effort freshness)
                self.logger.info(f"[LLM] Cache hit for prompt (hash={prompt_hash[:8]})")
                db.set_llm_cache(prompt_hash, cache_entry["prompt"], cache_entry["response"])  # bump usage

                # Return a simple object mimicking provider response
                class CachedResp:
                    def __init__(self, text):
                        self.text = text

                return CachedResp(cache_entry["response"])
        except Exception:
            # Cache unavailable - continue
            pass

        # Track attempts through provider chain
        attempted = set()

        while self._current and self._current not in attempted:
            attempted.add(self._current)
            try:
                result = self._current.generate_content(prompt)

                # Best-effort: store in cache and log usage
                try:
                    import hashlib

                    from db_manager import get_db

                    db = get_db()
                    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
                    resp_text = getattr(result, "text", str(result))
                    db.set_llm_cache(prompt_hash, prompt, resp_text)
                    # Extract tokens/cost if provider reports them
                    provider_name = getattr(self._current, "name", "unknown")
                    tokens_used, cost = _extract_usage_from_response(result)
                    db.log_llm_usage(provider_name, tokens_used=tokens_used, cost=cost)
                except Exception:
                    pass

                return result
            except Exception as e:
                self._primary_failures += 1
                error_type = "quota" if self._is_quota_error(e) else "error"
                self.logger.warning(f"[LLM] {self._current.name} {error_type}: {str(e)[:60]}")

                # Try to switch to next provider
                if not self._switch_to_next(f"{error_type}: {str(e)[:40]}"):
                    raise RuntimeError(f"All LLM providers failed. Last error: {e}")

        raise RuntimeError("All LLM providers exhausted")


def create_llm_provider(config: "Config", logger: logging.Logger) -> Optional[LLMProvider]:
    """
    Create a robust LLM provider with automatic fallback.

    Provider Priority (configurable):
    - Default: Gemini → Ollama → Local LLM
    - PREFER_LOCAL_LLM=1: Local → Ollama → Gemini
    - LLM_PROVIDER=local: Local only (no cloud)
    - LLM_PROVIDER=ollama: Ollama only
    - LLM_PROVIDER=gemini: Gemini only

    Returns a FallbackLLMProvider that automatically switches
    on quota errors, rate limits, or API failures.
    """
    # Use FallbackLLMProvider which handles all provider logic
    provider = FallbackLLMProvider(config, logger)
    if provider.is_available:
        return provider

    logger.warning("[LLM] No AI provider available")
    return None


def _extract_usage_from_response(resp: Any) -> tuple[int, float]:
    """Attempt to extract tokens_used and cost from provider response object/dict.

    Returns (tokens_used, cost) with defaults (0, 0.0).
    """
    tokens = 0
    cost = 0.0
    try:
        # Prefer provider-specific parsers for accurate metrics
        try:
            from scripts.llm_adapters import parse_gemini_usage, parse_generic_usage, parse_ollama_usage
        except Exception:
            parse_gemini_usage = parse_ollama_usage = parse_generic_usage = None

        # If provider is Gemini-like
        if parse_gemini_usage is not None:
            t, c = parse_gemini_usage(resp)
            if t or c:
                return t, c

        # If provider is Ollama-like
        if parse_ollama_usage is not None:
            t, c = parse_ollama_usage(resp)
            if t or c:
                return t, c

        # Fallback generic parser
        if parse_generic_usage is not None:
            t, c = parse_generic_usage(resp)
            tokens = int(t or 0)
            cost = float(c or 0.0)
    except Exception:
        pass
    return tokens, cost


# ==========================================
# CONFIGURATION
# ==========================================
@dataclass
class Config:
    """Central configuration with sensible defaults."""

    # API Configuration
    # Read API key from environment; do not hardcode secrets
    GEMINI_API_KEY: str = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY", ""))
    # Use an available model name from Google GenAI model list.
    # Default will work for the current API: 'models/gemini-pro-latest'
    GEMINI_MODEL: str = "models/gemini-pro-latest"

    # Local LLM Configuration
    # LOCAL_LLM_MODEL: Path to GGUF model file
    LOCAL_LLM_MODEL: str = field(default_factory=lambda: os.environ.get("LOCAL_LLM_MODEL", ""))
    # PREFER_LOCAL_LLM: Set to 1/true to always use local LLM instead of Gemini
    PREFER_LOCAL_LLM: bool = field(
        default_factory=lambda: os.environ.get("PREFER_LOCAL_LLM", "").lower() in ("1", "true", "yes")
    )
    # LOCAL_LLM_GPU_LAYERS: Number of layers to offload to GPU (0=CPU, -1=all)
    # Use robust parsing that tolerates commented or malformed env values via module helper
    LOCAL_LLM_GPU_LAYERS: int = field(default_factory=lambda: _get_env_int("LOCAL_LLM_GPU_LAYERS", 0))
    # LOCAL_LLM_AUTO_DOWNLOAD: Auto-download a model if none found (1/true)
    LOCAL_LLM_AUTO_DOWNLOAD: bool = field(
        default_factory=lambda: os.environ.get("LOCAL_LLM_AUTO_DOWNLOAD", "").lower() in ("1", "true", "yes")
    )

    # Ollama Configuration
    # OLLAMA_HOST: Ollama server URL
    OLLAMA_HOST: str = field(default_factory=lambda: os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
    # OLLAMA_MODEL: Ollama model name
    OLLAMA_MODEL: str = field(default_factory=lambda: os.environ.get("OLLAMA_MODEL", "llama3.2"))

    # Filesystem paths
    BASE_DIR: str = field(default_factory=lambda: os.path.dirname(os.path.abspath(__file__)))

    @property
    def OUTPUT_DIR(self) -> str:
        return os.path.join(self.BASE_DIR, "output")

    @property
    def CHARTS_DIR(self) -> str:
        return os.path.join(self.OUTPUT_DIR, "charts")

    @property
    def DATA_DIR(self) -> str:
        """Data directory for persistent storage (used in Docker containers)."""
        return os.path.join(self.BASE_DIR, "data")

    @property
    def MEMORY_FILE(self) -> str:
        """Cortex memory file - stored in data directory for Docker volume persistence."""
        data_dir = self.DATA_DIR
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "cortex_memory.json")

    @property
    def LOCK_FILE(self) -> str:
        """Lock file for cortex memory - stored in data directory for Docker compatibility."""
        data_dir = self.DATA_DIR
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "cortex_memory.lock")

    # Technical Analysis Thresholds
    ADX_TREND_THRESHOLD: float = 25.0
    GSR_HIGH_THRESHOLD: float = 85.0  # Gold/Silver ratio - Silver cheap
    GSR_LOW_THRESHOLD: float = 75.0  # Gold/Silver ratio - Gold cheap
    VIX_HIGH_THRESHOLD: float = 20.0  # High volatility threshold
    RSI_OVERBOUGHT: float = 70.0
    RSI_OVERSOLD: float = 30.0

    # Data Settings
    DATA_PERIOD: str = "1y"
    DATA_INTERVAL: str = "1d"
    CHART_CANDLE_COUNT: int = 100
    MAX_HISTORY_ENTRIES: int = 5
    MAX_CHART_AGE_DAYS: int = 7

    # Scheduling - NEW: Minutes-based for high-frequency operation
    # Default to 1-minute cycles for real-time intelligence
    RUN_INTERVAL_MINUTES: int = 1
    RUN_INTERVAL_HOURS: int = 4  # Default autonomous interval in hours (prefer multi-hour cycles)

    # Insights & Task Execution
    ENABLE_INSIGHTS_EXTRACTION: bool = True
    ENABLE_TASK_EXECUTION: bool = True
    MAX_TASKS_PER_CYCLE: int = 10

    # File Organization
    ENABLE_AUTO_ORGANIZE: bool = True
    ARCHIVE_DAYS_THRESHOLD: int = 7


# Asset Universe Configuration
ASSETS: Dict[str, Dict[str, str]] = {
    "GOLD": {"p": "GC=F", "b": "GLD", "name": "Gold Futures"},
    "SILVER": {"p": "SI=F", "b": "SLV", "name": "Silver Futures"},
    "DXY": {"p": "DX-Y.NYB", "b": "UUP", "name": "Dollar Index"},
    "YIELD": {"p": "^TNX", "b": "IEF", "name": "US 10Y Yield"},
    "VIX": {"p": "^VIX", "b": "^VIX", "name": "Volatility Index"},
    "SPX": {"p": "^GSPC", "b": "SPY", "name": "S&P 500"},
}

# Global state for graceful shutdown
shutdown_requested = False


# ==========================================
# LOGGING SETUP
# ==========================================
def setup_logging(config: Config) -> logging.Logger:
    """Configure structured logging with file and console handlers."""
    logger = logging.getLogger("GoldStandard")
    logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Console handler with unified formatting using scripts.console_ui
    try:
        from scripts.console_ui import format_log_message

        class ConsoleFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                level = record.levelname
                module = record.name
                msg = super().format(record)
                try:
                    return format_log_message(level, msg, module)
                except Exception:
                    return msg

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(ConsoleFormatter("%(message)s"))
        logger.addHandler(console_handler)
    except Exception:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

    # File handler for detailed logs (rotating)
    log_file = os.path.join(config.OUTPUT_DIR, "syndicate.log")
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s")
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    return logger


def strip_emojis(text: str) -> str:
    """Remove common emoji characters from a text string.
    This uses Unicode ranges for emoji and other symbols and removes them.
    """
    try:
        import re

        emoji_pattern = re.compile(
            "[\U0001f600-\U0001f64f"  # emoticons
            "\U0001f300-\U0001f5ff"  # symbols & pictographs
            "\U0001f680-\U0001f6ff"  # transport & map symbols
            "\U0001f700-\U0001f77f"  # alchemical symbols
            "\U0001f780-\U0001f7ff"  # Geometric Shapes Extended
            "\U0001f800-\U0001f8ff"  # Supplemental Arrows-C
            "\U0001f900-\U0001f9ff"  # Supplemental Symbols and Pictographs
            "\U0001fa00-\U0001fa6f"  # Chess Symbols etc
            "\U00002600-\U000026ff"  # Misc symbols
            "\U00002700-\U000027bf"  # Dingbats
            "]+",
            flags=re.UNICODE,
        )
        return emoji_pattern.sub(r"", text)
    except Exception:
        # Fallback: naive filter keeping ascii and basic punctuation
        return "".join(ch for ch in text if ord(ch) < 10000)


# ==========================================
# SIGNAL HANDLING
# ==========================================
def signal_handler(signum: int, frame: Any) -> None:
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger = logging.getLogger("GoldStandard")
    logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
    shutdown_requested = True


# ==========================================
# MODULE 1: MEMORY & REFLECTION (CORTEX)
# ==========================================
class Cortex:
    """
    Advanced persistent memory system for the Syndicate algo.
    Tracks predictions, grades performance, and manages hypothetical trade positions.
    Uses file locking to prevent corruption from concurrent access.
    """

    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        # Legacy filelock removed; use DB-backed cortex_memory exclusively with file fallback migration
        self.memory = self._load_memory()

    def _load_memory(self) -> Dict[str, Any]:
        """Load memory from JSON file with file locking."""
        default_memory = {
            # Prediction tracking
            "history": [],
            "win_streak": 0,
            "loss_streak": 0,
            "total_wins": 0,
            "total_losses": 0,
            "last_bias": None,
            "last_price_gold": 0.0,
            "last_update": None,
            # Trade simulation
            "active_trades": [],
            "closed_trades": [],
            "total_pnl": 0.0,
            "trade_count": 0,
            # Strategic context
            "current_regime": "UNKNOWN",
            "confidence_level": 0.5,
            "invalidation_triggers": [],
            "key_levels": {"support": [], "resistance": [], "stop_loss": None, "take_profit": []},
        }

        # Prefer storing memory in the central database for atomic updates and concurrency.
        try:
            from db_manager import get_db

            db = get_db()
            mem = db.get_cortex_memory()
            if mem:
                self.logger.info("Loaded cortex memory from database (cortex_memory table)")
                return {**default_memory, **mem}

            # If DB has no cortex_memory yet, try migrating legacy memory file into DB
            if os.path.exists(self.config.MEMORY_FILE):
                try:
                    with open(self.config.MEMORY_FILE, "r", encoding="utf-8") as f:
                        file_mem = json.load(f)
                    db.set_cortex_memory(file_mem)
                    self.logger.info("Migrated legacy memory file into DB cortex_memory and will use DB going forward")
                    # Optionally keep file as backup; do not require filelock
                    return {**default_memory, **file_mem}
                except Exception as e:
                    self.logger.warning(f"Failed to migrate memory file to DB: {e}")

        except Exception:
            # DB unavailable - fall back to file-based memory as legacy behavior
            self.logger.debug("DB unavailable for cortex memory; using file fallback")

        try:
            template_path = os.path.join(self.config.BASE_DIR, "cortex_memory.template.json")
            if not os.path.exists(self.config.MEMORY_FILE) and os.path.exists(template_path):
                with open(template_path, "r", encoding="utf-8") as t:
                    template_content = t.read()
                with open(self.config.MEMORY_FILE, "w", encoding="utf-8") as f:
                    f.write(template_content)
                # Log creation
                self.logger.info(f"Initialized new memory file from template: {self.config.MEMORY_FILE}")

            if os.path.exists(self.config.MEMORY_FILE):
                with open(self.config.MEMORY_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.logger.info(f"Successfully loaded memory from {self.config.MEMORY_FILE} (file fallback)")
                    return {**default_memory, **loaded}
            else:
                self.logger.warning(
                    f"Memory file not found at {self.config.MEMORY_FILE}. Starting with default memory."
                )
        except filelock.Timeout:
            self.logger.error(
                f"Could not acquire memory file lock for {self.config.MEMORY_FILE} (timeout). Another process might be holding it.",
                exc_info=True,
            )
        except json.JSONDecodeError as e:
            self.logger.error(
                f"Memory file {self.config.MEMORY_FILE} corrupted: {e}. Starting fresh with default memory.",
                exc_info=True,
            )
        except Exception as e:
            self.logger.error(f"Unexpected error loading memory from {self.config.MEMORY_FILE}: {e}", exc_info=True)

        return default_memory

    def _save_memory(self) -> bool:
        """Persist memory to JSON file."""
        # Prefer saving memory to DB for atomic writes
        try:
            from db_manager import get_db

            db = get_db()
            db.set_cortex_memory(self.memory)
            self.logger.info("Successfully saved cortex memory to database (cortex_memory table)")
            # Also write a file fallback asynchronously (best-effort)
            try:
                with open(self.config.MEMORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.memory, f, indent=4)
            except Exception:
                pass
            return True
        except Exception:
            # DB not available - fallback to file-based save
            try:
                with open(self.config.MEMORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.memory, f, indent=4)
                self.logger.info(f"Successfully saved memory to {self.config.MEMORY_FILE} (file fallback)")
                return True
            except Exception as e:
                self.logger.error(f"Unexpected error saving memory to {self.config.MEMORY_FILE}: {e}", exc_info=True)
        return False

    def update_memory(
        self,
        bias: str,
        current_gold_price: float,
        regime: str = None,
        confidence: float = None,
        key_levels: Dict = None,
    ) -> None:
        """Save current state for the next run to judge."""
        self.memory["last_bias"] = bias
        self.memory["last_price_gold"] = current_gold_price
        self.memory["last_update"] = datetime.datetime.now().isoformat()

        if regime:
            self.memory["current_regime"] = regime
        if confidence is not None:
            self.memory["confidence_level"] = confidence
        if key_levels:
            self.memory["key_levels"].update(key_levels)

        self._save_memory()
        self.logger.debug(f"Memory updated: bias={bias}, price={current_gold_price}")

    # ------------------------------------------
    # Trade Simulation System
    # ------------------------------------------
    def open_trade(
        self,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: List[float],
        size: float = 1.0,
        rationale: str = "",
    ) -> Dict:
        """
        Open a hypothetical trade position.
        Direction: LONG or SHORT
        """
        trade = {
            "id": self.memory.get("trade_count", 0) + 1,
            "direction": direction.upper(),
            "entry_price": entry_price,
            "entry_time": datetime.datetime.now().isoformat(),
            "stop_loss": stop_loss,
            "take_profit": take_profit if isinstance(take_profit, list) else [take_profit],
            "size": size,
            "rationale": rationale,
            "status": "OPEN",
            "current_price": entry_price,
            "unrealized_pnl": 0.0,
            "unrealized_pnl_pct": 0.0,
            "partial_exits": [],
            "trailing_stop": None,
        }

        self.memory["active_trades"].append(trade)
        self.memory["trade_count"] = trade["id"]
        self._save_memory()

        self.logger.info(f"[TRADE] Opened {direction} @ ${entry_price:.2f} | SL: ${stop_loss:.2f} | TP: {take_profit}")
        return trade

    def update_trade_prices(self, current_prices: Dict[str, float]) -> List[Dict]:
        """
        Update all active trades with current prices.
        Returns list of any trades that hit SL or TP.
        """
        gold_price = current_prices.get("GOLD", 0)
        if not gold_price:
            return []

        triggered_trades = []

        for trade in self.memory.get("active_trades", []):
            if trade["status"] != "OPEN":
                continue

            trade["current_price"] = gold_price
            entry = trade["entry_price"]
            direction = trade["direction"]

            # Calculate unrealized PnL
            if direction == "LONG":
                pnl = (gold_price - entry) * trade["size"]
                pnl_pct = ((gold_price - entry) / entry) * 100
            else:  # SHORT
                pnl = (entry - gold_price) * trade["size"]
                pnl_pct = ((entry - gold_price) / entry) * 100

            trade["unrealized_pnl"] = round(pnl, 2)
            trade["unrealized_pnl_pct"] = round(pnl_pct, 2)

            # Check stop loss
            if direction == "LONG" and gold_price <= trade["stop_loss"]:
                trade["exit_reason"] = "STOP_LOSS"
                triggered_trades.append(trade)
            elif direction == "SHORT" and gold_price >= trade["stop_loss"]:
                trade["exit_reason"] = "STOP_LOSS"
                triggered_trades.append(trade)

            # Check take profits (first target)
            if trade["take_profit"]:
                first_tp = trade["take_profit"][0]
                if direction == "LONG" and gold_price >= first_tp:
                    trade["exit_reason"] = "TAKE_PROFIT"
                    triggered_trades.append(trade)
                elif direction == "SHORT" and gold_price <= first_tp:
                    trade["exit_reason"] = "TAKE_PROFIT"
                    triggered_trades.append(trade)

        self._save_memory()
        return triggered_trades

    def close_trade(self, trade_id: int, exit_price: float, reason: str = "MANUAL") -> Optional[Dict]:
        """Close an active trade and record results."""
        for i, trade in enumerate(self.memory.get("active_trades", [])):
            if trade["id"] == trade_id:
                # Calculate final PnL
                entry = trade["entry_price"]
                direction = trade["direction"]

                if direction == "LONG":
                    pnl = (exit_price - entry) * trade["size"]
                    pnl_pct = ((exit_price - entry) / entry) * 100
                else:
                    pnl = (entry - exit_price) * trade["size"]
                    pnl_pct = ((entry - exit_price) / entry) * 100

                # Update trade record
                trade["status"] = "CLOSED"
                trade["exit_price"] = exit_price
                trade["exit_time"] = datetime.datetime.now().isoformat()
                trade["exit_reason"] = reason
                trade["realized_pnl"] = round(pnl, 2)
                trade["realized_pnl_pct"] = round(pnl_pct, 2)
                trade["result"] = "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "BREAKEVEN"

                # Move to closed trades
                self.memory["active_trades"].pop(i)
                self.memory["closed_trades"].append(trade)
                self.memory["total_pnl"] = round(self.memory.get("total_pnl", 0) + pnl, 2)

                # Update win/loss stats
                if trade["result"] == "WIN":
                    self.memory["total_wins"] = self.memory.get("total_wins", 0) + 1
                    self.memory["win_streak"] = self.memory.get("win_streak", 0) + 1
                    self.memory["loss_streak"] = 0
                elif trade["result"] == "LOSS":
                    self.memory["total_losses"] = self.memory.get("total_losses", 0) + 1
                    self.memory["loss_streak"] = self.memory.get("loss_streak", 0) + 1
                    self.memory["win_streak"] = 0

                self._save_memory()
                self.logger.info(
                    f"[TRADE] Closed #{trade_id} @ ${exit_price:.2f} | "
                    f"PnL: ${pnl:.2f} ({pnl_pct:+.2f}%) | {trade['result']}"
                )
                return trade

        return None

    def update_trailing_stop(self, trade_id: int, new_stop: float) -> bool:
        """Update trailing stop for an active trade."""
        for trade in self.memory.get("active_trades", []):
            if trade["id"] == trade_id:
                old_stop = trade["stop_loss"]
                trade["stop_loss"] = new_stop
                trade["trailing_stop"] = new_stop
                self._save_memory()
                self.logger.info(f"[TRADE] Updated SL for #{trade_id}: ${old_stop:.2f} -> ${new_stop:.2f}")
                return True
        return False

    def get_active_trades(self) -> List[Dict]:
        """Get all active trade positions."""
        return self.memory.get("active_trades", [])

    def get_trade_summary(self) -> Dict:
        """Get trading performance summary."""
        closed = self.memory.get("closed_trades", [])
        active = self.memory.get("active_trades", [])

        total_trades = len(closed)
        wins = sum(1 for t in closed if t.get("result") == "WIN")
        losses = sum(1 for t in closed if t.get("result") == "LOSS")

        return {
            "total_trades": total_trades,
            "active_positions": len(active),
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / total_trades * 100) if total_trades > 0 else 0,
            "total_pnl": self.memory.get("total_pnl", 0),
            "win_streak": self.memory.get("win_streak", 0),
            "loss_streak": self.memory.get("loss_streak", 0),
        }

    # ------------------------------------------
    # Legacy Performance Grading
    # ------------------------------------------

    def grade_performance(self, current_gold_price: float) -> str:
        """Check if the previous run's bias was correct and update statistics."""
        if not self.memory.get("last_bias") or self.memory.get("last_price_gold", 0) == 0:
            self.logger.info("No previous prediction to grade")
            return "NO HISTORY"

        prev_price = self.memory["last_price_gold"]
        bias = self.memory["last_bias"]
        delta = current_gold_price - prev_price
        delta_pct = (delta / prev_price) * 100 if prev_price else 0

        result = "NEUTRAL"
        if bias == "BULLISH" and delta > 0:
            result = "WIN"
            self.memory["win_streak"] = self.memory.get("win_streak", 0) + 1
            self.memory["loss_streak"] = 0
            self.memory["total_wins"] = self.memory.get("total_wins", 0) + 1
        elif bias == "BULLISH" and delta < 0:
            result = "LOSS"
            self.memory["loss_streak"] = self.memory.get("loss_streak", 0) + 1
            self.memory["win_streak"] = 0
            self.memory["total_losses"] = self.memory.get("total_losses", 0) + 1
        elif bias == "BEARISH" and delta < 0:
            result = "WIN"
            self.memory["win_streak"] = self.memory.get("win_streak", 0) + 1
            self.memory["loss_streak"] = 0
            self.memory["total_wins"] = self.memory.get("total_wins", 0) + 1
        elif bias == "BEARISH" and delta > 0:
            result = "LOSS"
            self.memory["loss_streak"] = self.memory.get("loss_streak", 0) + 1
            self.memory["win_streak"] = 0
            self.memory["total_losses"] = self.memory.get("total_losses", 0) + 1

        # Log the result
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "prev_bias": bias,
            "prev_price": prev_price,
            "current_price": current_gold_price,
            "delta_pct": round(delta_pct, 2),
            "result": result,
        }
        self.memory["history"].append(entry)

        # Keep history bounded
        max_history = self.config.MAX_HISTORY_ENTRIES
        if len(self.memory["history"]) > max_history:
            self.memory["history"] = self.memory["history"][-max_history:]

        self.logger.info(
            f"Performance graded: {bias} @ ${prev_price:.2f} -> ${current_gold_price:.2f} "
            f"({delta_pct:+.2f}%) = {result}"
        )

        return result

    def get_win_rate(self) -> Optional[float]:
        """Calculate win rate percentage."""
        total = self.memory.get("total_wins", 0) + self.memory.get("total_losses", 0)
        if total == 0:
            return None
        return (self.memory.get("total_wins", 0) / total) * 100

    def get_formatted_history(self) -> str:
        """Format history for AI context."""
        if not self.memory.get("history"):
            return "No previous predictions recorded."

        lines = []
        for entry in self.memory["history"]:
            if isinstance(entry, dict):
                lines.append(
                    f"- {entry.get('prev_bias', 'N/A')} @ ${entry.get('prev_price', 0):.2f} "
                    f"-> ${entry.get('current_price', 0):.2f} ({entry.get('delta_pct', 0):+.2f}%) = "
                    f"{entry.get('result', 'N/A')}"
                )
            else:
                # Legacy string format
                lines.append(f"- {entry}")

        win_rate = self.get_win_rate()
        stats = f"\nWin Rate: {win_rate:.1f}%" if win_rate is not None else ""
        streak_info = ""
        if self.memory.get("win_streak", 0) > 0:
            streak_info = f" | Current Win Streak: {self.memory['win_streak']}"
        elif self.memory.get("loss_streak", 0) > 0:
            streak_info = f" | Current Loss Streak: {self.memory['loss_streak']}"

        return "\n".join(lines) + stats + streak_info


# ==========================================
# MODULE 2: QUANT ENGINE (Data)
# ==========================================
class QuantEngine:
    """
    Handles market data fetching, technical indicator calculation, and chart generation.
    """

    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.news: List[str] = []
        # Track charts generated during this QuantEngine instance (single run)
        # Charts will only be skipped if they were already created earlier in
        # the same run. This avoids re-using stale on-disk charts from
        # previous runs while preventing duplicate generation within one loop.
        self._generated_charts = set()
        # Production mode: using ASSETS defined in the source configuration

    def get_data(self) -> Optional[Dict[str, Any]]:
        """Fetch and process data for all tracked assets."""
        self.logger.info("Engaging Quant Engine - fetching market data...")
        self.logger.info("[SYSTEM] Engaging Quant Engine...")

        snapshot: Dict[str, Any] = {}
        self.news = []

        # Ensure charts directory exists
        os.makedirs(self.config.CHARTS_DIR, exist_ok=True)

        # Clean up old charts
        self._cleanup_old_charts()

        # Fetch data for each asset in parallel to reduce wall time
        # Use single-threaded fetch to avoid yfinance concurrency issues that may
        # cause mismatched or duplicated data across assets.
        workers = 1
        futures = {}
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for key, conf in ASSETS.items():
                conf = ASSETS[key]
                futures[ex.submit(self._fetch, conf["p"], conf["b"])] = (key, conf)

            from concurrent.futures import as_completed

            for fut in as_completed(futures):
                key, conf = futures[fut]
                try:
                    df = fut.result()
                    if df is None or df.empty:
                        self.logger.warning(f"No data available for {key}")
                        continue

                    latest = df.iloc[-1]
                    previous = df.iloc[-2] if len(df) > 1 else latest

                    # Safely extract values with validation
                    close_price = self._safe_float(latest.get("Close"))
                    prev_close = self._safe_float(previous.get("Close"))
                    rsi = self._safe_float(latest.get("RSI"))
                    adx = self._safe_float(latest.get("ADX_14"))
                    atr = self._safe_float(latest.get("ATR"))
                    sma200 = self._safe_float(latest.get("SMA_200"))

                    if close_price is None:
                        self.logger.warning(f"Invalid close price for {key}")
                        continue

                    # Calculate change percentage
                    change_pct = 0.0
                    if prev_close and prev_close != 0:
                        change_pct = ((close_price - prev_close) / prev_close) * 100

                    # Determine market regime based on ADX
                    regime = "UNKNOWN"
                    if adx is not None:
                        regime = "TRENDING" if adx > self.config.ADX_TREND_THRESHOLD else "CHOPPY/RANGING"

                    snapshot[key] = {
                        "price": round(close_price, 2),
                        "change": round(change_pct, 2),
                        "rsi": round(rsi, 2) if rsi is not None else None,
                        "adx": round(adx, 2) if adx is not None else None,
                        "atr": round(atr, 2) if atr is not None else None,
                        "regime": regime,
                        "sma200": round(sma200, 2) if sma200 is not None else None,
                    }

                    # Persist snapshot to DB for historical use (best-effort)
                    try:
                        from db_manager import AnalysisSnapshot, get_db

                        snap = AnalysisSnapshot(
                            date=str(datetime.date.today()),
                            asset=key,
                            price=snapshot[key]["price"],
                            rsi=snapshot[key].get("rsi"),
                            sma_50=None,
                            sma_200=snapshot[key].get("sma200"),
                            atr=snapshot[key].get("atr"),
                            adx=snapshot[key].get("adx"),
                            trend=snapshot[key].get("regime"),
                            raw_data=None,
                        )
                        get_db().save_analysis_snapshot(snap)
                    except Exception as _:
                        self.logger.debug("Failed to persist analysis snapshot", exc_info=True)

                    # Fetch news headlines
                    self._fetch_news(key, conf["p"])

                    # Generate chart (cached - skip if up-to-date)
                    try:
                        self._chart(key, df)
                    except Exception as c_err:
                        self.logger.debug(f"Chart generation skipped/failed for {key}: {c_err}")

                    self.logger.debug(f"Processed {key}: ${close_price:.2f} ({change_pct:+.2f}%)")

                except Exception as e:
                    self.logger.error(f"Error processing {key}: {e}", exc_info=True)
                    continue

        if not snapshot:
            self.logger.error("Failed to fetch any market data")
            return None

        # Diagnostic: detect uniform prices across assets which is a sign
        # of an upstream mapping or aggregation bug.
        try:
            prices = [v.get("price") for v in snapshot.values() if isinstance(v, dict) and "price" in v]
            unique_prices = set(prices)
            if len(prices) > 1 and len(unique_prices) == 1:
                msg = f"Uniform prices detected across assets: {unique_prices}. This may indicate a mapping/fetch bug."
                self.logger.warning(msg)
                try:
                    # Increment a metrics counter if available
                    try:
                        from syndicate.metrics.server import METRICS

                        if METRICS and "uniform_price_alerts_total" in METRICS:
                            METRICS["uniform_price_alerts_total"].inc()
                    except Exception:
                        # metric increment is non-critical
                        self.logger.debug("Failed to increment uniform_price_alerts_total metric", exc_info=True)

                    # Send an alert to the configured Discord webhook to notify operators
                    from scripts.notifier import send_discord

                    send_discord(f"[Syndicate] {msg}")
                except Exception:
                    # Non-critical: log failure to send alert but do not fail the run
                    self.logger.debug("Failed to send uniform-price alert", exc_info=True)
        except Exception:
            # Non-critical diagnostic - do not fail the run
            pass

        # Calculate intermarket ratios
        snapshot = self._compute_intermarket_ratios(snapshot)

        return snapshot

    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float."""
        if value is None:
            return None
        try:
            result = float(value)
            if pd.isna(result):
                return None
            return result
        except (ValueError, TypeError):
            return None

    def _compute_intermarket_ratios(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Compute and attach intermarket ratios such as GSR to the snapshot.

        Uses historic prices from the database as a fallback when current
        snapshot data for an asset is missing or invalid.
        """
        # Local import to avoid circular dependency at module import time
        try:
            from db_manager import get_db
        except Exception:
            get_db = None

        gold_price = None
        silver_price = None

        if "GOLD" in snapshot:
            gold_price = snapshot["GOLD"].get("price")
        if "SILVER" in snapshot:
            silver_price = snapshot["SILVER"].get("price")

        # Fallback: use latest historic price from DB when missing
        if (silver_price is None or silver_price == 0) and get_db:
            try:
                silver_price = get_db().get_latest_price("SILVER")
                if silver_price:
                    self.logger.debug(f"Using fallback historic silver price: {silver_price}")
            except Exception as e:
                self.logger.debug(f"Failed to fetch historic silver price: {e}")

        if (gold_price is None or gold_price == 0) and get_db:
            try:
                gold_price = get_db().get_latest_price("GOLD")
                if gold_price:
                    self.logger.debug(f"Using fallback historic gold price: {gold_price}")
            except Exception as e:
                self.logger.debug(f"Failed to fetch historic gold price: {e}")

        try:
            gold_price_f = self._safe_float(gold_price)
            silver_price_f = self._safe_float(silver_price)
            if gold_price_f is not None and silver_price_f is not None and silver_price_f > 0:
                gsr = round(gold_price_f / silver_price_f, 2)
                snapshot["RATIOS"] = {"GSR": gsr}
                self.logger.info(f"Gold/Silver Ratio: {gsr}")
            else:
                self.logger.debug("GSR not computed: missing or invalid gold/silver prices")
        except Exception as e:
            self.logger.debug(f"Failed to compute GSR: {e}")

        return snapshot

    def _fetch(self, primary: str, backup: str) -> Optional[pd.DataFrame]:
        """Fetch market data with fallback to backup ticker."""
        # Production path: fetch from yfinance only

        for ticker in [primary, backup]:
            try:
                self.logger.debug(f"Fetching data for {ticker}")
                df = yf.download(
                    ticker,
                    period=self.config.DATA_PERIOD,
                    interval=self.config.DATA_INTERVAL,
                    progress=False,
                    multi_level_index=False,
                    auto_adjust=True,
                )

                if df.empty:
                    self.logger.debug(f"No data returned for {ticker}")
                    continue

                # Validate minimal columns exist
                required_columns = ["Open", "High", "Low", "Close"]

                def _has_col(df, col):
                    if col in df.columns:
                        return True
                    if isinstance(df.columns, pd.MultiIndex):
                        return col in df.columns.get_level_values(0)
                    return False

                if not all(_has_col(df, col) for col in required_columns):
                    self.logger.warning(f"Missing required OHLC columns for {ticker}: {df.columns}")
                    continue

                # Ensure index is timezone-aware or normalized
                df.index = pd.to_datetime(df.index)

                # Calculate technical indicators safely with fallbacks
                def safe_indicator_series(name, func, *fargs, **fkwargs):
                    try:
                        import numpy as _np

                        out = func(*fargs, **fkwargs)
                        if out is None:
                            return None

                        # If DataFrame: try to extract a sensible single column
                        if isinstance(out, pd.DataFrame):
                            if out.shape[1] == 1:
                                s = out.iloc[:, 0]
                            else:
                                # Prefer column containing the indicator name, else first numeric column
                                cols = [c for c in out.columns if name.upper() in str(c).upper()]
                                if cols:
                                    s = out[cols[0]]
                                else:
                                    # fall back to first column
                                    s = out.iloc[:, 0]

                        elif isinstance(out, pd.Series):
                            s = out

                        else:
                            # ndarray / list / scalar
                            try:
                                arr = _np.asarray(out)
                            except Exception:
                                # last resort: build a series and try to reindex
                                s = pd.Series(out)
                            else:
                                if arr.ndim == 0:
                                    # scalar
                                    s = pd.Series([arr[()]] * len(df), index=df.index)
                                elif arr.ndim == 1:
                                    if arr.size == len(df):
                                        s = pd.Series(arr, index=df.index)
                                    elif 0 < arr.size < len(df):
                                        # right-align shorter result to the tail of df
                                        idx = df.index[-arr.size :]
                                        s = pd.Series(arr, index=idx)
                                        s = s.reindex(df.index)
                                    else:
                                        # unexpected length; coerce to series and attempt reindex
                                        s = pd.Series(arr)
                                else:
                                    # multi-dim: take first column and try to align
                                    first_col = arr[:, 0]
                                    if first_col.size == len(df):
                                        s = pd.Series(first_col, index=df.index)
                                    elif 0 < first_col.size < len(df):
                                        idx = df.index[-first_col.size :]
                                        s = pd.Series(first_col, index=idx)
                                        s = s.reindex(df.index)
                                    else:
                                        s = pd.Series(first_col)

                        # Final alignment: ensure series index matches df index length
                        try:
                            if len(s) != len(df):
                                s = s.reindex(df.index)
                        except Exception:
                            pass

                        if len(s) != len(df):
                            self.logger.warning(
                                f"Indicator {name} returned {len(s)} values for {ticker} but df has {len(df)} index; ignoring {name}"
                            )
                            return None

                        # Ensure numeric dtype
                        return pd.to_numeric(s, errors="coerce")
                    except Exception as e:
                        self.logger.warning(f"Safe indicator {name} failed for {ticker}: {e}")
                        return None

                # Compute indicators with backoff to fallback implementations
                try:
                    # RSI
                    rsi_series = safe_indicator_series("RSI", ta.rsi, df["Close"], length=14)
                    if rsi_series is None:
                        # fallback computation (coerce multi-column Close to single Series if needed)
                        close_src = df["Close"]
                        if isinstance(close_src, pd.DataFrame):
                            # prefer column that contains 'Close' in its name, else first numeric column
                            cols = [c for c in close_src.columns if "close" in str(c).lower()]
                            if cols:
                                close_src = close_src[cols[0]]
                            else:
                                close_src = close_src.iloc[:, 0]

                        delta = close_src.diff()
                        up = delta.clip(lower=0)
                        down = -delta.clip(upper=0)
                        ma_up = up.rolling(window=14, min_periods=14).mean()
                        ma_down = down.rolling(window=14, min_periods=14).mean()
                        rs = ma_up / ma_down
                        rsi_series = 100 - (100 / (1 + rs))
                except Exception as e:
                    self.logger.warning(f"RSI computation failed for {ticker}: {e}")
                    rsi_series = None

                try:
                    sma200 = safe_indicator_series("SMA_200", ta.sma, df["Close"], length=200)
                    if sma200 is None:
                        # fallback SMA using pandas rolling mean (coerce multi-column Close)
                        close_src = df["Close"]
                        if isinstance(close_src, pd.DataFrame):
                            cols = [c for c in close_src.columns if "close" in str(c).lower()]
                            if cols:
                                close_src = close_src[cols[0]]
                            else:
                                close_src = close_src.iloc[:, 0]
                        sma200 = close_src.rolling(window=200, min_periods=1).mean()
                except Exception as e:
                    self.logger.warning(f"SMA_200 computation failed for {ticker}: {e}")
                    # fallback SMA using pandas rolling mean
                    try:
                        sma200 = df["Close"].rolling(window=200, min_periods=1).mean()
                    except Exception:
                        sma200 = None

                try:
                    sma50 = safe_indicator_series("SMA_50", ta.sma, df["Close"], length=50)
                    if sma50 is None:
                        # fallback SMA using pandas rolling mean (coerce multi-column Close)
                        close_src = df["Close"]
                        if isinstance(close_src, pd.DataFrame):
                            cols = [c for c in close_src.columns if "close" in str(c).lower()]
                            if cols:
                                close_src = close_src[cols[0]]
                            else:
                                close_src = close_src.iloc[:, 0]
                        sma50 = close_src.rolling(window=50, min_periods=1).mean()
                except Exception as e:
                    self.logger.warning(f"SMA_50 computation failed for {ticker}: {e}")
                    # fallback SMA using pandas rolling mean
                    try:
                        sma50 = df["Close"].rolling(window=50, min_periods=1).mean()
                    except Exception:
                        sma50 = None

                try:
                    atr_series = safe_indicator_series("ATR", ta.atr, df["High"], df["Low"], df["Close"], length=14)
                    if atr_series is None:
                        # fallback ATR as rolling mean of TR
                        prev_close = df["Close"].shift(1)
                        tr1 = df["High"] - df["Low"]
                        tr2 = (df["High"] - prev_close).abs()
                        tr3 = (df["Low"] - prev_close).abs()
                        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                        atr_series = tr.rolling(window=14, min_periods=14).mean()
                except Exception as e:
                    self.logger.warning(f"ATR computation failed for {ticker}: {e}")
                    atr_series = None

                # ADX returns DataFrame with multiple columns. Wrap safely and make it robust to
                # irregular input shapes (DataFrame vs Series), missing indices, and divide-by-zero.
                try:
                    adx_df = None
                    raw_adx = None
                    try:
                        raw_adx = ta.adx(df["High"], df["Low"], df["Close"], length=14)
                    except Exception:
                        raw_adx = None

                    if isinstance(raw_adx, pd.DataFrame):
                        adx_df = raw_adx

                    if adx_df is None:
                        # fallback ADX (robust version)
                        # Coerce inputs to Series and align their indices
                        high = df["High"]
                        low = df["Low"]
                        close = df["Close"]

                        if isinstance(high, pd.DataFrame):
                            high = high.iloc[:, 0]
                        if isinstance(low, pd.DataFrame):
                            low = low.iloc[:, 0]
                        if isinstance(close, pd.DataFrame):
                            close = close.iloc[:, 0]

                        common_index = high.index.intersection(low.index).intersection(close.index)
                        high = high.reindex(common_index)
                        low = low.reindex(common_index)
                        close = close.reindex(common_index)

                        prev_close = close.shift(1)
                        tr1 = high - low
                        tr2 = (high - prev_close).abs()
                        tr3 = (low - prev_close).abs()
                        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                        atr = tr.rolling(window=14, min_periods=14).mean()

                        up_move = high.diff()
                        down_move = -low.diff()

                        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
                        minus_dm = (-down_move).where((down_move > up_move) & (down_move > 0), 0.0)

                        # Align to ATR index and guard divide-by-zero
                        plus_dm = plus_dm.reindex(atr.index)
                        minus_dm = minus_dm.reindex(atr.index)

                        atr_safe = atr.replace(0, pd.NA)

                        plus_di = (plus_dm.rolling(window=14, min_periods=14).sum() / atr_safe) * 100
                        minus_di = (minus_dm.rolling(window=14, min_periods=14).sum() / atr_safe) * 100

                        denom = (plus_di + minus_di).replace({0: pd.NA})
                        dx = (plus_di - minus_di).abs() / denom * 100
                        adx_ser = dx.rolling(window=14, min_periods=14).mean()

                        adx_df = pd.DataFrame(
                            {"ADX_14": adx_ser, "DMP_14": plus_di, "DMN_14": minus_di}, index=adx_ser.index
                        )
                except Exception as e:
                    self.logger.warning(f"ADX computation failed for {ticker}: {e}")
                    adx_df = None

                # Assign computed indicators if present
                if rsi_series is not None:
                    df["RSI"] = rsi_series
                if sma200 is not None:
                    df["SMA_200"] = sma200
                if sma50 is not None:
                    df["SMA_50"] = sma50
                if atr_series is not None:
                    df["ATR"] = atr_series
                if adx_df is not None:
                    df = pd.concat([df, adx_df], axis=1)

                # Only drop rows based on missing OHLC data — keep indicator NaNs to avoid dropping datasets
                # Support MultiIndex columns by normalizing required OHLC columns to single-level
                subset_cols = []
                for col in ["Open", "High", "Low", "Close"]:
                    if col in df.columns:
                        subset_cols.append(col)
                    elif isinstance(df.columns, pd.MultiIndex) and col in df.columns.get_level_values(0):
                        # pick first matching level-1 column and expose it as a single-level column
                        for c in df.columns:
                            if c[0] == col:
                                try:
                                    df[col] = df[c]
                                except Exception:
                                    # if df[c] is a DataFrame, pick first inner column
                                    if isinstance(df[c], pd.DataFrame):
                                        df[col] = df[c].iloc[:, 0]
                                subset_cols.append(col)
                                break

                try:
                    df_clean = df.dropna(subset=subset_cols)
                except Exception:
                    # conservative fallback: require presence of explicit columns only
                    df_clean = df.dropna(subset=[c for c in ["Open", "High", "Low", "Close"] if c in df.columns])

                if not df_clean.empty:
                    return df_clean

            except Exception as e:
                self.logger.warning(f"Error fetching {ticker}: {e}")
                continue

        return None

    def _fetch_news(self, asset_key: str, ticker: str) -> None:
        """Fetch latest news headline for an asset."""
        try:
            t = yf.Ticker(ticker)
            if hasattr(t, "news") and t.news:
                headline = t.news[0].get("title", "")
                if headline:
                    self.news.append(f"{asset_key}: {headline}")
                    self.logger.debug(f"News for {asset_key}: {headline[:50]}...")
        except Exception as e:
            self.logger.debug(f"Could not fetch news for {asset_key}: {e}")

    def _chart(self, name: str, df: pd.DataFrame) -> None:
        """Generate candlestick chart with technical overlays."""
        try:
            # Determine chart path
            chart_path = os.path.join(self.config.CHARTS_DIR, f"{name}.png")

            # Only skip generation if this chart was already produced earlier
            # during the same run. Do NOT rely on on-disk mtimes from previous
            # runs — we want each run to produce a fresh, consistent set.
            if name in getattr(self, "_generated_charts", set()):
                self.logger.info(f"Chart already generated in this run, skipping: {chart_path}")
                return

            # Prepare additional plots
            # Prefer columns if precomputed by _fetch; else compute safely
            def safe_sma(series, length):
                try:
                    out = None
                    # Try using ta if available
                    out = ta.sma(series, length)
                    if out is None:
                        raise Exception("ta.sma returned None")
                    if isinstance(out, pd.Series):
                        s = out
                    else:
                        s = pd.Series(out, index=series.index)
                    if len(s) != len(series):
                        raise Exception("sma length mismatch")
                    return s
                except Exception:
                    # fallback to pandas rolling mean
                    try:
                        return series.rolling(window=length, min_periods=length).mean()
                    except Exception:
                        return None

            if "SMA_50" in df.columns:
                sma50 = df["SMA_50"]
            else:
                sma50 = safe_sma(df["Close"], 50)
            if "SMA_200" in df.columns:
                sma200 = df["SMA_200"]
            else:
                sma200 = safe_sma(df["Close"], 200)

            # Slice the dataframe to the candle count to plot; additionally slice addplot series to match length
            plot_df = df.tail(self.config.CHART_CANDLE_COUNT)
            apds = []
            sma50_plot = None
            sma200_plot = None
            if sma50 is not None:
                sma50_plot = sma50.reindex(plot_df.index)
            if sma200 is not None:
                sma200_plot = sma200.reindex(plot_df.index)
            # Build addplot dataframes but defer calling `mpf.make_addplot` until
            # mplfinance is imported (below). This avoids calling into mpf at
            # module-import time.
            # `apds` remains an array of mpl addplots after the import stage.

            # Ensure mpl/mplfinance are imported with a headless backend
            try:
                if mpf is None:
                    import matplotlib

                    # Respect `MPLBACKEND` env var when provided, default to Agg
                    matplotlib.use(os.environ.get("MPLBACKEND", "Agg"))
                    import mplfinance as mpf_mod

                    # bind local mpf for subsequent calls in this process
                    globals()["mpf"] = mpf_mod

                mpf_local = globals().get("mpf")
                if mpf_local is None:
                    raise RuntimeError("mplfinance not available after import attempt")

                # Build addplots now that mpf_local is available
                apds = []
                if sma50_plot is not None and hasattr(sma50_plot, "isna") and not sma50_plot.isna().all():
                    apds.append(mpf_local.make_addplot(sma50_plot, color="orange", width=1))
                if sma200_plot is not None and hasattr(sma200_plot, "isna") and not sma200_plot.isna().all():
                    apds.append(mpf_local.make_addplot(sma200_plot, color="blue", width=1))

                style = mpf_local.make_mpf_style(base_mpf_style="nightclouds", rc={"font.size": 8})
                chart_path = os.path.join(self.config.CHARTS_DIR, f"{name}.png")

                plot_kwargs = {
                    "type": "candle",
                    "volume": False,
                    "style": style,
                    "title": f"{name} Quant View",
                    "savefig": chart_path,
                }

                if apds:
                    plot_kwargs["addplot"] = apds
                mpf_local.plot(plot_df, **plot_kwargs)
                # Mark as generated for this run so subsequent calls in the
                # same execution loop don't regenerate the same chart.
                try:
                    self._generated_charts.add(name)
                except Exception:
                    pass
            except Exception as e:
                self.logger.warning(f"Skipping chart generation (mplfinance unavailable or failed): {e}")
            # ensure chart was actually written
            ok = False
            try:
                if os.path.exists(chart_path) and os.path.getsize(chart_path) > 2048:
                    ok = True
            except Exception:
                ok = False

            if not ok:
                self.logger.warning(
                    f"Chart generated but verification failed (size too small or missing): {chart_path}"
                )
            else:
                self.logger.info(f"Chart generated and verified: {chart_path}")

        except Exception as e:
            self.logger.error(f"Error generating chart for {name}: {e}")

    def _cleanup_old_charts(self) -> None:
        """Remove charts older than configured age."""
        if not os.path.exists(self.config.CHARTS_DIR):
            return

        try:
            cutoff = datetime.datetime.now() - datetime.timedelta(days=self.config.MAX_CHART_AGE_DAYS)

            for filename in os.listdir(self.config.CHARTS_DIR):
                if not filename.endswith(".png"):
                    continue

                filepath = os.path.join(self.config.CHARTS_DIR, filename)
                file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))

                if file_mtime < cutoff:
                    os.remove(filepath)
                    self.logger.debug(f"Removed old chart: {filename}")

        except Exception as e:
            self.logger.warning(f"Error during chart cleanup: {e}")


# ==========================================
# MODULE 3: THE STRATEGIST (AI)
# ==========================================
class Strategist:
    """
    AI-powered market analysis using Google Gemini.
    Generates sophisticated trading insights matching institutional-grade analysis.
    """

    def __init__(
        self,
        config: Config,
        logger: logging.Logger,
        data: Dict[str, Any],
        news: List[str],
        memory_log: str,
        model: Optional[Any] = None,
        cortex: Optional["Cortex"] = None,
    ):
        self.config = config
        self.logger = logger
        self.data = data
        self.news = news
        self.memory = memory_log
        self.model = model
        self.cortex = cortex

    def think(self) -> Tuple[str, str]:
        """Generate AI analysis and extract trading bias."""
        self.logger.info("AI Strategist analyzing correlations & volatility...")

        if "GOLD" not in self.data:
            self.logger.error("Gold data missing - cannot generate analysis")
            return "Error: Gold data unavailable", "NEUTRAL"

        gsr = self.data.get("RATIOS", {}).get("GSR", "N/A")
        vix_data = self.data.get("VIX", {})
        vix_price = vix_data.get("price", "N/A")

        data_dump = self._format_data_summary()
        prompt = self._build_prompt(gsr, vix_price, data_dump)

        try:
            # Enforce Gemini-only for journal generation (strict policy)
            try:
                gem = GeminiProvider(self.config.GEMINI_MODEL)
                response = gem.generate_content(prompt)
                response_text = response.text
            except Exception as ge:
                self.logger.error(f"Gemini generation failed for Journal (strict): {ge}", exc_info=True)
                return f"Error generating journal with Gemini: {ge}", "NEUTRAL"

            bias = self._extract_bias(response_text)
            self.logger.info(f"AI analysis complete. Bias: {bias}")
            return response_text, bias

        except Exception as e:
            self.logger.error(f"Unexpected AI generation error: {e}", exc_info=True)
            return f"Error generating analysis: {e}", "NEUTRAL"

    def _format_data_summary(self) -> str:
        """Format asset data for AI prompt."""
        lines = []
        for key, values in self.data.items():
            if key == "RATIOS":
                continue
            if not isinstance(values, dict):
                continue

            price = values.get("price", "N/A")
            change = values.get("change", 0)
            rsi = values.get("rsi", "N/A")
            adx = values.get("adx", "N/A")
            regime = values.get("regime", "N/A")
            atr = values.get("atr", "N/A")
            sma200 = values.get("sma200", "N/A")

            trend_vs_sma = ""
            if price != "N/A" and sma200 and sma200 != "N/A":
                if price > sma200:
                    trend_vs_sma = "ABOVE 200SMA"
                else:
                    trend_vs_sma = "BELOW 200SMA"

            lines.append(
                f"* {key}: ${price} ({change:+.2f}%) | RSI: {rsi} | ADX: {adx} ({regime}) | ATR: ${atr} | {trend_vs_sma}"
            )

        return "\n".join(lines)

    def _get_active_trades_context(self) -> str:
        """Format active trades for AI context."""
        if not self.cortex:
            return "No active positions."

        trades = self.cortex.get_active_trades()
        if not trades:
            return "No active positions."

        lines = ["Current Active Positions:"]
        for t in trades:
            lines.append(
                f"* Trade #{t['id']}: {t['direction']} @ ${t['entry_price']:.2f} | "
                f"SL: ${t['stop_loss']:.2f} | TP: {t['take_profit']} | "
                f"Unrealized: ${t.get('unrealized_pnl', 0):.2f} ({t.get('unrealized_pnl_pct', 0):+.2f}%)"
            )
        return "\n".join(lines)

    def _build_prompt(self, gsr: Any, vix_price: Any, data_dump: str) -> str:
        """Build sophisticated AI analysis prompt matching institutional style."""
        gold_data = self.data.get("GOLD", {})
        gold_price = gold_data.get("price", 0)
        gold_atr = gold_data.get("atr", 0) or 0
        gold_rsi = gold_data.get("rsi", 50)
        gold_adx = gold_data.get("adx", 0)

        atr_stop_width = float(gold_atr) * 2
        suggested_sl = gold_price - atr_stop_width if gold_price else 0
        suggested_tp1 = gold_price + (atr_stop_width * 1.5) if gold_price else 0
        suggested_tp2 = gold_price + (atr_stop_width * 3) if gold_price else 0

        # Determine regime
        regime = "TRENDING" if gold_adx and gold_adx > self.config.ADX_TREND_THRESHOLD else "RANGE-BOUND/CHOPPY"

        # Get active trades context
        trades_context = self._get_active_trades_context()

        return f"""
You are "Syndicate" - an elite quantitative trading algorithm operating for a sophisticated hedge fund.
Your analysis must be precise, actionable, and reflect deep market understanding.

=== SYSTEM STATE ===
Performance Memory:
{self.memory}

Active Positions:
{trades_context}

=== MARKET TELEMETRY ===
{data_dump}

Intermarket Ratios:
* Gold/Silver Ratio (GSR): {gsr} (>85 = Silver undervalued; <75 = Gold undervalued)
* VIX (Fear Gauge): {vix_price} (>20 = Elevated volatility/risk-off; <15 = Complacency)

Current Regime Detection: {regime} (ADX: {gold_adx})

=== NEWS CONTEXT ===
{chr(10).join(["* " + n for n in self.news[:5]]) if self.news else "No significant headlines."}

=== ANALYSIS FRAMEWORK ===

Generate a comprehensive trading journal following this EXACT structure:

## Date: {datetime.date.today().strftime("%B %d, %Y")}

---

## 1. Market Context
Analyze the broader macro environment:
* Fed policy expectations and rate probabilities
* Dollar dynamics and their impact on commodities
* Global liquidity conditions and risk appetite
* Key macro themes driving precious metals

## 2. Asset-Specific Analysis
For Gold and the metals complex:
* Current price action and technical structure
* Trend strength (use ADX: {gold_adx})
* Momentum readings (RSI: {gold_rsi})
* Key support/resistance zones
* Intermarket correlations (GSR, DXY relationship)

## 3. Sentiment Summary
* Institutional positioning (infer from price action)
* Safe-haven demand dynamics
* Market pulse (bullish/bearish/neutral sentiment)

## 4. Strategic Thesis
**Bias:** **[BULLISH/BEARISH/NEUTRAL]** (Choose ONE and make it bold)

Provide clear rationale with:
* Primary thesis (1-2 sentences)
* Supporting factors (bullet points)
* Invalidation conditions (what would change your view)

## 5. Setup Scan & Trade Idea

| Component | Specification |
|-----------|---------------|
| Direction | LONG / SHORT / FLAT |
| Entry Zone | Price range for entry |
| Stop Loss | ${suggested_sl:.2f} (2x ATR: ${atr_stop_width:.2f}) |
| Target 1 | ${suggested_tp1:.2f} (1.5R) |
| Target 2 | ${suggested_tp2:.2f} (3R) |
| Position Sizing | Based on ATR volatility |

Entry Conditions:
* List specific conditions that must be met

## 6. Scenario Probability Matrix

| Scenario | Price Target | Probability | Key Drivers |
|----------|-------------|-------------|-------------|
| Bull Case | $X,XXX | XX% | List drivers |
| Base Case | $X,XXX | XX% | List drivers |
| Bear Case | $X,XXX | XX% | List drivers |

## 7. Risk Management
* Key levels to watch
* Trailing stop strategy
* Position adjustment triggers

## 8. Algo Self-Reflection
* Previous call assessment (from memory)
* Lessons learned
* Confidence calibration

---
*Generated by Syndicate Quant Engine*
"""

    def _extract_bias(self, text: str) -> str:
        """Extract trading bias from AI response using robust parsing."""
        text_upper = text.upper()

        bias_patterns = [
            r"\*\*BIAS[:\*\s]*\*?\*?\s*\*?\*?(BULLISH|BEARISH|NEUTRAL)",
            r"BIAS[:\s]+\*?\*?(BULLISH|BEARISH|NEUTRAL)",
            r"\*\*(BULLISH|BEARISH|NEUTRAL)\*\*",
            r"DIRECTION[:\s]+(LONG|SHORT|FLAT)",
        ]

        for pattern in bias_patterns:
            match = re.search(pattern, text_upper)
            if match:
                result = match.group(1)
                if result == "LONG":
                    return "BULLISH"
                elif result == "SHORT":
                    return "BEARISH"
                elif result == "FLAT":
                    return "NEUTRAL"
                return result

        bullish_count = text_upper.count("BULLISH") + text_upper.count("LONG")
        bearish_count = text_upper.count("BEARISH") + text_upper.count("SHORT")
        neutral_count = text_upper.count("NEUTRAL") + text_upper.count("FLAT")

        if bullish_count > bearish_count and bullish_count > neutral_count:
            return "BULLISH"
        elif bearish_count > bullish_count and bearish_count > neutral_count:
            return "BEARISH"

        return "NEUTRAL"


# ==========================================
# EXECUTION LOOP
# ==========================================
def execute(
    config: Config,
    logger: logging.Logger,
    model: Optional[Any] = None,
    dry_run: bool = False,
    no_ai: bool = False,
    force: bool = False,
) -> bool:
    """
    Execute one analysis cycle.
    Returns True on success, False on failure.
    """
    logger.info("=" * 50)
    logger.info("QUANT CYCLE INITIATED")
    logger.info("=" * 50)

    # Ensure output directory exists
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    # Initialize components
    cortex = Cortex(config, logger)
    quant = QuantEngine(config, logger)
    # The legacy `force` flag is no longer used. Chart generation skips only
    # duplicate charts produced earlier in the same run; on-disk charts from
    # previous runs do not prevent fresh generation in a new run.

    # 1. Get Market Data
    data = quant.get_data()
    if not data:
        logger.error("Data fetch failed - aborting cycle")
        return False

    # Validate gold data exists
    if "GOLD" not in data:
        logger.error("Gold data missing - aborting cycle")
        return False

    gold_price = data["GOLD"]["price"]

    # 2. Grade Past Performance
    last_result = cortex.grade_performance(gold_price)
    logger.info(f"[MEMORY] Last Run Result: {last_result}")

    # 3. Update active trades with current prices
    triggered = cortex.update_trade_prices({"GOLD": gold_price})
    for trade in triggered:
        logger.info(f"[TRADE] Auto-closed: #{trade['id']} - {trade.get('exit_reason', 'TRIGGERED')}")
        cortex.close_trade(trade["id"], gold_price, trade.get("exit_reason", "AUTO"))

    # 4. AI Analysis
    memory_context = cortex.get_formatted_history()
    report = ""
    new_bias = "NEUTRAL"

    if no_ai:
        logger.info("No-AI mode enabled; skipping AI analysis")
        report = "[NO AI MODE] - AI analysis skipped by CLI option."
        new_bias = "NEUTRAL"
    else:
        strat = Strategist(config, logger, data, quant.news, memory_context, model=model, cortex=cortex)
        report, new_bias = strat.think()

    # 5. Save Bias to Memory (unless dry-run)
    if not dry_run:
        cortex.update_memory(new_bias, gold_price)
    else:
        logger.info("Dry-run mode: memory not updated")

    # Remove any existing today's journal so a fresh one can be created
    try:
        fname = os.path.join(config.OUTPUT_DIR, f"Journal_{datetime.date.today()}.md")
        if os.path.exists(fname):
            os.remove(fname)
            logger.info(f"Deleted previous journal: {fname}")
    except Exception as e:
        logger.warning(f"Failed deleting previous journal: {e}")

    # 6. Write Report
    report_filename = f"Journal_{datetime.date.today()}.md"
    report_path = os.path.join(config.OUTPUT_DIR, report_filename)

    if dry_run:
        logger.info(f"Dry-run mode: skipping report write to {report_path}")
        return True

    try:
        # Clean non-ASCII / emoji characters from report before saving
        safe_report = strip_emojis(report)

        # Apply frontmatter with correct AI status
        # This ensures the document has proper lifecycle tracking from creation
        try:
            from scripts.frontmatter import add_frontmatter

            ai_was_used = not no_ai and "[NO AI MODE]" not in safe_report
            lifecycle_status = "in_progress" if ai_was_used else "draft"
            safe_report = add_frontmatter(
                safe_report, report_filename, status=lifecycle_status, ai_processed=ai_was_used
            )
        except ImportError:
            pass  # Frontmatter module not available

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(safe_report)
            f.write("\n\n---\n\n## Charts\n\n")
            f.write("![Gold](charts/GOLD.png)\n\n")
            f.write("![Silver](charts/SILVER.png)\n\n")
            f.write("![VIX](charts/VIX.png)\n")

        # Instrument charts/report generation for Prometheus if available
        try:
            from syndicate.metrics import METRICS

            METRICS["charts_generated_total"].inc()
        except Exception:
            pass

        logger.info(f"Report generated: {report_path}")

        # Save to database for organized storage
        try:
            from db_manager import JournalEntry, get_db

            db = get_db()

            # Get silver price and GSR for database
            silver_price = data.get("SILVER", {}).get("price", 0)
            # Prefer computed RATIOS if present, otherwise compute safely here
            gsr = data.get("RATIOS", {}).get("GSR")
            if gsr is None:
                try:
                    g_price = float(gold_price) if gold_price is not None else 0
                    s_price = float(silver_price) if silver_price is not None else 0
                    gsr = round(g_price / s_price, 2) if s_price > 0 else 0
                except Exception:
                    gsr = 0

            entry = JournalEntry(
                date=str(datetime.date.today()),
                content=safe_report,
                bias=new_bias,
                gold_price=gold_price,
                silver_price=silver_price,
                gsr=gsr,
                ai_enabled=not no_ai,
            )
            db.save_journal(entry, overwrite=True)
            logger.info(f"[DATABASE] Journal saved for {datetime.date.today()}")

            # Register document in lifecycle system
            # Status is 'in_progress' if AI processed, 'draft' if no-AI mode
            lifecycle_status = "in_progress" if not no_ai else "draft"
            db.register_document(
                report_path,
                doc_type="journal",
                status=lifecycle_status,
                content_hash=db.get_file_hash(report_path) if hasattr(db, "get_file_hash") else None,
            )
            logger.debug(f"[LIFECYCLE] Registered journal with status: {lifecycle_status}")

        except ImportError:
            logger.debug("Database module not available, skipping DB save")
        except Exception as db_err:
            logger.warning(f"Failed to save to database: {db_err}")

        # Run live analysis if AI enabled (catalysts, institutional matrix, horizon reports)
        if not no_ai and model:
            try:
                from scripts.live_analysis import LiveAnalyzer

                analyzer = LiveAnalyzer(config, logger, model)
                logger.info("[LIVE] Running live analysis suite...")

                # Generate all live reports
                reports_generated = analyzer.run_full_analysis(
                    gold_price=gold_price, silver_price=data.get("SILVER", {}).get("price", 0), current_bias=new_bias
                )

                for report_name, report_path in reports_generated.items():
                    logger.info(f"[LIVE] Generated: {report_name} -> {report_path}")

            except ImportError as ie:
                logger.debug(f"Live analysis module not available: {ie}")
            except Exception as la_err:
                logger.warning(f"Live analysis failed: {la_err}")

        return True

    except Exception as e:
        logger.error(f"Error writing report: {e}", exc_info=True)
        return False


def main() -> None:
    """Main entry point with graceful shutdown handling."""
    global shutdown_requested

    # Load environment from .env (optional)
    # (Already loaded at module import time)

    # Parse CLI arguments
    parser = argparse.ArgumentParser(description="Syndicate Quant Analysis")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument(
        "--wait", action="store_true", help="Wait (bounded by timeout) for post-analysis tasks to complete before exit"
    )
    parser.add_argument(
        "--wait-forever",
        action="store_true",
        help="Wait indefinitely until no tasks, no new insights, and all documents are published to Notion before exiting",
    )
    parser.add_argument("--dry-run", action="store_true", help="Run without writing memory/report")
    parser.add_argument("--no-ai", action="store_true", help="Do not call AI, produce a skeleton report")
    parser.add_argument("--force", "-f", action="store_true", help="Force regenerate charts and re-run expensive steps")
    parser.add_argument("--interval", type=int, default=None, help="Override run interval hours")
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    parser.add_argument("--gemini-key", default=None, help="Override GEMINI API key via CLI (not recommended)")
    # Production mode: the tool uses the configured ASSETS in the source code
    args = parser.parse_args()

    # Initialize colorama
    init(autoreset=True)

    # Load configuration
    config = Config()
    if args.interval:
        config.RUN_INTERVAL_HOURS = args.interval

    # Setup logging
    logger = setup_logging(config)
    # Adjust log level from CLI
    logger.setLevel(getattr(logging, args.log_level.upper(), logging.INFO))

    # Start metrics server (Prometheus) if available
    try:
        from syndicate.metrics import set_readiness, start_metrics_server

        start_metrics_server()
        # Mark readiness; modules may update later
        set_readiness(True)
        logger.info("Metrics server started (prometheus) on port %s", os.getenv("METRICS_PORT", "8000"))
    except Exception:
        logger.debug("Prometheus metrics server not available or failed to start")
    # Create an LLM provider unless --no-ai is set. Do not require Gemini API key
    model_obj = None
    if not args.no_ai:
        try:
            provider = create_llm_provider(config, logger)
            if provider:
                model_obj = provider
                logger.info(f"LLM provider available: {provider.name}")
            else:
                logger.warning(
                    "No LLM provider available; continuing without AI. Use --no-ai to suppress this message or configure an LLM provider."
                )
                model_obj = None
        except Exception as e:
            logger.warning(f"Failed to initialize LLM providers: {e}. Continuing without AI.")
            model_obj = None

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Render startup banner in the console if available
    try:
        from scripts.console_ui import render_system_banner

        render_system_banner("Syndicate", f"Run interval: {config.RUN_INTERVAL_HOURS} hours")
    except Exception:
        logger.info("GOLD STANDARD SYSTEM ONLINE")
        logger.info(f"Run interval: {config.RUN_INTERVAL_HOURS} hours")
        logger.info("Press Ctrl+C to shutdown gracefully")

    # Execute immediately
    execute(config, logger, model=model_obj, dry_run=args.dry_run, no_ai=args.no_ai, force=args.force)

    # If --once, run post-analysis tasks (insights, task execution, Notion sync) then exit
    if args.once:
        logger.info("Run-once mode specified -- running post-analysis tasks (insights, tasks, Notion sync)")
        try:
            # Import run module and invoke post-analysis handler (safe: run.main isn't executed on import)
            import run as run_script  # noqa: E402

            # Default wait-forever behavior unless explicit flags provided
            wait_forever_flag = args.wait_forever or (not args.wait and not args.wait_forever)
            run_script._run_post_analysis_tasks(
                force_inline=(args.wait or wait_forever_flag),
                wait_for_completion=args.wait,
                wait_forever=wait_forever_flag,
            )
        except Exception as e:
            logger.warning(f"Post-analysis tasks failed: {e}")
        logger.info("Run-once mode complete -- exiting")
        return

    # Schedule recurring execution
    schedule.every(config.RUN_INTERVAL_HOURS).hours.do(
        execute, config, logger, model_obj, args.dry_run, args.no_ai, args.force
    )

    # Main loop with graceful shutdown
    while not shutdown_requested:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(5)

    logger.info("Graceful shutdown complete")


if __name__ == "__main__":
    main()
