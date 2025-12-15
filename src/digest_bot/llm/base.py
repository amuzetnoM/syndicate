#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════════════
#  Digest Bot - LLM Base Interface
#  Copyright (c) 2025 SIRIUS Alpha
# ══════════════════════════════════════════════════════════════════════════════
"""
Abstract base class for LLM providers.

Defines the contract that all LLM backends must implement.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


class ProviderError(Exception):
    """Base exception for LLM provider errors."""

    def __init__(self, message: str, provider: str, retryable: bool = True):
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable


class ModelNotFoundError(ProviderError):
    """Raised when the specified model cannot be found."""

    def __init__(self, model_path: str, provider: str):
        super().__init__(f"Model not found: {model_path}", provider=provider, retryable=False)
        self.model_path = model_path


class InferenceError(ProviderError):
    """Raised when inference fails."""

    pass


class ConnectionError(ProviderError):
    """Raised when connection to provider fails."""

    pass


@dataclass
class LLMResponse:
    """
    Response from an LLM provider.

    Attributes:
        text: Generated text content
        tokens_used: Number of tokens consumed
        generation_time: Time taken for generation in seconds
        model: Model identifier used
        provider: Provider name
        finish_reason: Why generation stopped (e.g., 'stop', 'length')
        raw_response: Original response from provider (for debugging)
    """

    text: str
    tokens_used: int = 0
    generation_time: float = 0.0
    model: str = ""
    provider: str = ""
    finish_reason: str = "stop"
    raw_response: Optional[dict] = None

    @property
    def is_truncated(self) -> bool:
        """Check if response was truncated due to token limit."""
        return self.finish_reason == "length"

    @property
    def tokens_per_second(self) -> float:
        """Calculate tokens per second."""
        if self.generation_time > 0:
            return self.tokens_used / self.generation_time
        return 0.0

    def __str__(self) -> str:
        return self.text

    def __repr__(self) -> str:
        return (
            f"LLMResponse(provider={self.provider!r}, model={self.model!r}, "
            f"tokens={self.tokens_used}, time={self.generation_time:.2f}s)"
        )


@dataclass
class GenerationConfig:
    """
    Configuration for text generation.

    Attributes:
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0.0 = deterministic)
        top_p: Nucleus sampling probability
        top_k: Top-k sampling
        stop_sequences: Sequences that stop generation
        repeat_penalty: Penalty for repeating tokens
    """

    max_tokens: int = 512
    temperature: float = 0.3
    top_p: float = 0.9
    top_k: int = 40
    stop_sequences: list = field(default_factory=list)
    repeat_penalty: float = 1.1

    def to_dict(self) -> dict:
        """Convert to dictionary for provider APIs."""
        return {
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "stop": self.stop_sequences,
            "repeat_penalty": self.repeat_penalty,
        }


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All LLM backends must implement this interface to ensure
    consistent behavior across different inference engines.
    """

    name: str = "base"

    def __init__(self):
        self._loaded = False
        self._model_name = ""

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded and ready."""
        return self._loaded

    @property
    def model_name(self) -> str:
        """Get the loaded model name."""
        return self._model_name

    @abstractmethod
    def load(self) -> None:
        """
        Load the model into memory.

        Raises:
            ModelNotFoundError: If model file doesn't exist
            ProviderError: If loading fails
        """
        pass

    @abstractmethod
    def unload(self) -> None:
        """
        Unload the model and free resources.
        """
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> LLMResponse:
        """
        Generate text from a prompt.

        Args:
            prompt: Input text to generate from
            config: Generation configuration (uses defaults if None)

        Returns:
            LLMResponse with generated text and metadata

        Raises:
            InferenceError: If generation fails
            ProviderError: For other provider errors
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the provider is healthy and ready.

        Returns:
            True if ready to generate, False otherwise
        """
        pass

    def generate_with_retry(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> LLMResponse:
        """
        Generate with automatic retry on retryable errors.

        Args:
            prompt: Input text
            config: Generation config
            max_retries: Maximum retry attempts
            retry_delay: Base delay between retries (exponential backoff)

        Returns:
            LLMResponse on success

        Raises:
            ProviderError: After all retries exhausted
        """
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                return self.generate(prompt, config)
            except ProviderError as e:
                last_error = e
                if not e.retryable or attempt >= max_retries:
                    raise

                # Exponential backoff
                delay = retry_delay * (2**attempt)
                time.sleep(delay)

        # Should never reach here, but just in case
        raise last_error or ProviderError("Generation failed after retries", provider=self.name)

    def __enter__(self):
        """Context manager entry - load model."""
        self.load()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - unload model."""
        self.unload()
        return False

    def __repr__(self) -> str:
        status = "loaded" if self._loaded else "not loaded"
        return f"<{self.__class__.__name__} model={self._model_name!r} {status}>"
