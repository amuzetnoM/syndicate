#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════════════
#  Digest Bot - llama.cpp Provider
#  Copyright (c) 2025 SIRIUS Alpha
# ══════════════════════════════════════════════════════════════════════════════
"""
llama.cpp LLM provider using llama-cpp-python.

Provides on-device inference with CPU/GPU acceleration.
"""

import logging
import time
from pathlib import Path
from typing import Optional

from .base import (
    GenerationConfig,
    InferenceError,
    LLMProvider,
    LLMResponse,
    ModelNotFoundError,
    ProviderError,
)

logger = logging.getLogger(__name__)


class LlamaCppProvider(LLMProvider):
    """
    llama.cpp provider for local GGUF model inference.

    Uses llama-cpp-python for efficient CPU/GPU inference
    with quantized models.
    """

    name = "llamacpp"

    def __init__(
        self,
        model_path: Path,
        n_gpu_layers: int = 0,
        n_ctx: int = 4096,
        n_threads: int = 0,
        verbose: bool = False,
    ):
        """
        Initialize llama.cpp provider.

        Args:
            model_path: Path to GGUF model file
            n_gpu_layers: Number of layers to offload to GPU (0=CPU only, -1=all)
            n_ctx: Context window size
            n_threads: CPU threads (0=auto)
            verbose: Enable verbose llama.cpp output
        """
        super().__init__()
        self.model_path = Path(model_path).expanduser().resolve()
        self.n_gpu_layers = n_gpu_layers
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.verbose = verbose
        self._llm = None

    def load(self) -> None:
        """Load the GGUF model into memory."""
        if self._loaded:
            return

        # Validate model exists
        if not self.model_path.exists():
            raise ModelNotFoundError(str(self.model_path), self.name)

        # Validate file size (basic sanity check)
        file_size_mb = self.model_path.stat().st_size / (1024 * 1024)
        if file_size_mb < 100:
            raise ProviderError(
                f"Model file too small ({file_size_mb:.1f} MB). " "May be corrupted or incomplete.",
                provider=self.name,
                retryable=False,
            )

        logger.info(f"Loading model: {self.model_path.name} ({file_size_mb:.0f} MB)")

        try:
            # Import here to avoid startup cost if not using this provider
            from llama_cpp import Llama

            start = time.time()

            self._llm = Llama(
                model_path=str(self.model_path),
                n_gpu_layers=self.n_gpu_layers,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads if self.n_threads > 0 else None,
                verbose=self.verbose,
            )

            elapsed = time.time() - start
            self._loaded = True
            self._model_name = self.model_path.name

            logger.info(f"✓ Model loaded in {elapsed:.2f}s (llama.cpp)")

        except ImportError:
            raise ProviderError(
                "llama-cpp-python not installed. Install with:\n"
                "  pip install llama-cpp-python\n"
                "For GPU support:\n"
                "  CMAKE_ARGS='-DLLAMA_CUDA=on' pip install llama-cpp-python",
                provider=self.name,
                retryable=False,
            )
        except Exception as e:
            error_msg = str(e)
            # Check for common error patterns
            if "failed to load" in error_msg.lower():
                raise ProviderError(
                    f"Failed to load GGUF model. The file may be corrupted.\n"
                    f"Path: {self.model_path}\n"
                    f"Try re-downloading the model.",
                    provider=self.name,
                    retryable=False,
                )
            elif "out of memory" in error_msg.lower() or "malloc" in error_msg.lower():
                raise ProviderError(
                    f"Out of memory loading model ({file_size_mb:.0f} MB).\n"
                    f"Try a smaller quantization or close other applications.",
                    provider=self.name,
                    retryable=False,
                )
            else:
                raise ProviderError(f"Failed to load model: {error_msg}", provider=self.name, retryable=False)

    def unload(self) -> None:
        """Unload the model and free memory."""
        if self._llm is not None:
            del self._llm
            self._llm = None
        self._loaded = False
        self._model_name = ""
        logger.info("Model unloaded")

    def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> LLMResponse:
        """
        Generate text using llama.cpp.

        Args:
            prompt: Input prompt text
            config: Generation configuration

        Returns:
            LLMResponse with generated text
        """
        if not self._loaded:
            self.load()

        if config is None:
            config = GenerationConfig()

        try:
            start = time.time()

            logger.debug(f"Generating with max_tokens={config.max_tokens}, temp={config.temperature}")

            response = self._llm(
                prompt,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                top_p=config.top_p,
                top_k=config.top_k,
                stop=config.stop_sequences or None,
                repeat_penalty=config.repeat_penalty,
                echo=False,
            )

            elapsed = time.time() - start

            # Extract response data
            choice = response["choices"][0]
            text = choice["text"].strip()
            finish_reason = choice.get("finish_reason", "stop")

            # Token counts
            usage = response.get("usage", {})
            tokens_used = usage.get("completion_tokens", 0)
            prompt_tokens = usage.get("prompt_tokens", 0)

            logger.debug(
                f"Generation complete: prompt_tokens={prompt_tokens}, "
                f"completion_tokens={tokens_used}, finish_reason={finish_reason}, "
                f"text_len={len(text)}"
            )

            # Log warning if response seems truncated or empty
            if len(text) < 50:
                logger.warning(
                    f"Short response ({len(text)} chars). " f"finish_reason={finish_reason}, raw_text='{text[:100]}...'"
                )

            return LLMResponse(
                text=text,
                tokens_used=tokens_used,
                generation_time=elapsed,
                model=self._model_name,
                provider=self.name,
                finish_reason=finish_reason,
                raw_response=response,
            )

        except Exception as e:
            raise InferenceError(f"Generation failed: {e}", provider=self.name, retryable=True)

    def health_check(self) -> bool:
        """Check if llama.cpp is ready."""
        if not self._loaded:
            return False

        try:
            # Quick generation test
            response = self._llm("Hello", max_tokens=1, echo=False)
            return "choices" in response
        except Exception:
            return False

    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        if not self._loaded:
            return {"loaded": False}

        return {
            "loaded": True,
            "model": self._model_name,
            "path": str(self.model_path),
            "context_size": self.n_ctx,
            "gpu_layers": self.n_gpu_layers,
            "threads": self.n_threads,
        }
