#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════════════
#  Digest Bot - Ollama Provider
#  Copyright (c) 2025 SIRIUS Alpha
# ══════════════════════════════════════════════════════════════════════════════
"""
Ollama LLM provider for local server-based inference.

Connects to a running Ollama server for model management and inference.
"""

import logging
import time
from typing import Optional
from urllib.parse import urljoin

from .base import (
    ConnectionError,
    GenerationConfig,
    InferenceError,
    LLMProvider,
    LLMResponse,
    ModelNotFoundError,
    ProviderError,
)

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """
    Ollama provider for local LLM inference via HTTP API.

    Requires a running Ollama server (ollama serve).
    """

    name = "ollama"

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "mistral",
        timeout: float = 120.0,
    ):
        """
        Initialize Ollama provider.

        Args:
            host: Ollama server URL
            model: Model name (must be pulled first)
            timeout: Request timeout in seconds
        """
        super().__init__()
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._session = None

    def _get_session(self):
        """Get or create HTTP session."""
        if self._session is None:
            try:
                import requests

                self._session = requests.Session()
                self._session.headers.update(
                    {
                        "Content-Type": "application/json",
                    }
                )
            except ImportError:
                raise ProviderError(
                    "requests library not installed. Install with:\n" "  pip install requests",
                    provider=self.name,
                    retryable=False,
                )
        return self._session

    def _api_url(self, endpoint: str) -> str:
        """Build API URL."""
        return urljoin(self.host + "/", endpoint.lstrip("/"))

    def load(self) -> None:
        """
        Verify connection to Ollama and model availability.

        Note: Ollama loads models on-demand, so this just verifies
        the server is running and model exists.
        """
        if self._loaded:
            return

        session = self._get_session()

        # Check server health
        try:
            response = session.get(self._api_url("/api/tags"), timeout=10.0)
            response.raise_for_status()
        except Exception as e:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.host}\n" f"Ensure Ollama is running: ollama serve\n" f"Error: {e}",
                provider=self.name,
                retryable=True,
            )

        # Check model exists
        try:
            models = response.json().get("models", [])
            model_names = [m.get("name", "").split(":")[0] for m in models]

            if self.model not in model_names and f"{self.model}:latest" not in [m.get("name") for m in models]:
                available = ", ".join(model_names[:5])
                raise ModelNotFoundError(
                    f"Model '{self.model}' not found. Available: {available}\n" f"Pull with: ollama pull {self.model}",
                    provider=self.name,
                )
        except ModelNotFoundError:
            raise
        except Exception as e:
            logger.warning(f"Could not verify model availability: {e}")

        self._loaded = True
        self._model_name = self.model
        logger.info(f"Connected to Ollama at {self.host}, model: {self.model}")

    def unload(self) -> None:
        """Close the HTTP session."""
        if self._session is not None:
            self._session.close()
            self._session = None
        self._loaded = False
        self._model_name = ""
        logger.info("Ollama session closed")

    def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> LLMResponse:
        """
        Generate text using Ollama API.

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

        session = self._get_session()

        # Build request payload
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": config.max_tokens,
                "temperature": config.temperature,
                "top_p": config.top_p,
                "top_k": config.top_k,
                "repeat_penalty": config.repeat_penalty,
            },
        }

        if config.stop_sequences:
            payload["options"]["stop"] = config.stop_sequences

        try:
            start = time.time()

            response = session.post(
                self._api_url("/api/generate"),
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()

            elapsed = time.time() - start
            data = response.json()

            # Extract response
            text = data.get("response", "").strip()

            # Determine finish reason
            done_reason = data.get("done_reason", "stop")
            if data.get("done") and not done_reason:
                done_reason = "stop"

            # Token counts (Ollama provides eval_count)
            tokens_used = data.get("eval_count", 0)

            return LLMResponse(
                text=text,
                tokens_used=tokens_used,
                generation_time=elapsed,
                model=self._model_name,
                provider=self.name,
                finish_reason=done_reason,
                raw_response=data,
            )

        except Exception as e:
            if "timeout" in str(e).lower():
                raise InferenceError(
                    f"Ollama request timed out after {self.timeout}s", provider=self.name, retryable=True
                )
            raise InferenceError(f"Ollama generation failed: {e}", provider=self.name, retryable=True)

    def health_check(self) -> bool:
        """Check if Ollama server is healthy."""
        try:
            session = self._get_session()
            response = session.get(self._api_url("/api/tags"), timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """List available models on the Ollama server."""
        try:
            session = self._get_session()
            response = session.get(self._api_url("/api/tags"), timeout=10.0)
            response.raise_for_status()
            models = response.json().get("models", [])
            return [m.get("name", "") for m in models]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    def pull_model(self, model_name: str) -> bool:
        """
        Pull a model from Ollama registry.

        Args:
            model_name: Name of model to pull

        Returns:
            True if successful
        """
        try:
            session = self._get_session()
            response = session.post(
                self._api_url("/api/pull"),
                json={"name": model_name, "stream": False},
                timeout=600.0,  # Models can take a while
            )
            response.raise_for_status()
            logger.info(f"Successfully pulled model: {model_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False
