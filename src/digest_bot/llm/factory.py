#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════════════
#  Digest Bot - LLM Provider Factory
#  Copyright (c) 2025 SIRIUS Alpha
# ══════════════════════════════════════════════════════════════════════════════
"""
Factory for creating LLM providers based on configuration.

Provider priority (default):
1. llama.cpp (local) - Most reliable, no external dependencies
2. Ollama - Local server fallback

The factory automatically falls back to the next provider if the primary fails.
"""

import logging
from typing import List, Optional, Tuple

from .base import LLMProvider, ProviderError
from .llamacpp import LlamaCppProvider
from .ollama import OllamaProvider

logger = logging.getLogger(__name__)

# Provider priority order (first = highest priority)
PROVIDER_PRIORITY = ["local", "ollama"]

# Singleton provider instance
_provider: Optional[LLMProvider] = None


def create_provider(provider_type: str = "local", **kwargs) -> LLMProvider:
    """
    Create an LLM provider instance.

    Args:
        provider_type: Provider type ("local" for llama.cpp, "ollama")
        **kwargs: Provider-specific configuration

    Returns:
        Configured LLMProvider instance

    Raises:
        ProviderError: If provider type is unknown
    """
    provider_type = provider_type.lower()

    if provider_type in ("local", "llamacpp", "llama.cpp", "llama-cpp"):
        return LlamaCppProvider(
            model_path=kwargs.get("model_path"),
            n_gpu_layers=kwargs.get("n_gpu_layers", 0),
            n_ctx=kwargs.get("n_ctx", 4096),
            n_threads=kwargs.get("n_threads", 0),
            verbose=kwargs.get("verbose", False),
        )

    elif provider_type == "ollama":
        return OllamaProvider(
            host=kwargs.get("host", "http://localhost:11434"),
            model=kwargs.get("model", "mistral"),
            timeout=kwargs.get("timeout", 120.0),
        )

    else:
        raise ProviderError(
            f"Unknown provider type: {provider_type}\n" f"Available: local, ollama", provider="factory", retryable=False
        )


def create_provider_from_config(config, provider_override: Optional[str] = None) -> LLMProvider:
    """
    Create an LLM provider from a Config object.

    Args:
        config: Config object with llm settings
        provider_override: Force a specific provider type

    Returns:
        Configured LLMProvider instance
    """
    llm_config = config.llm
    provider_type = provider_override or llm_config.provider

    if provider_type == "local":
        return LlamaCppProvider(
            model_path=llm_config.local_model_path,
            n_gpu_layers=llm_config.local_gpu_layers,
            n_ctx=llm_config.local_context,
            n_threads=llm_config.local_threads,
            verbose=config.debug,
        )

    elif provider_type == "ollama":
        return OllamaProvider(
            host=llm_config.ollama_host,
            model=llm_config.ollama_model,
            timeout=120.0,
        )

    else:
        raise ProviderError(f"Unknown provider: {llm_config.provider}", provider="factory", retryable=False)


def get_provider(config=None) -> LLMProvider:
    """
    Get or create the global LLM provider instance.

    Args:
        config: Optional Config object (uses default if None)

    Returns:
        LLMProvider instance
    """
    global _provider

    if _provider is None:
        if config is None:
            from ..config import get_config

            config = get_config()

        _provider = create_provider_from_config(config)
        logger.info(f"Created LLM provider: {_provider.name}")

    return _provider


def reset_provider() -> None:
    """Reset the global provider (for testing)."""
    global _provider
    if _provider is not None:
        if _provider.is_loaded:
            _provider.unload()
        _provider = None


def switch_provider(provider_type: str, config=None) -> LLMProvider:
    """
    Switch to a different provider type.

    Args:
        provider_type: New provider type
        config: Optional Config object

    Returns:
        New LLMProvider instance
    """
    global _provider

    # Unload current provider
    reset_provider()

    # Get config
    if config is None:
        from ..config import get_config

        config = get_config()

    # Override provider type
    config.llm.provider = provider_type

    # Create new provider
    _provider = create_provider_from_config(config)
    logger.info(f"Switched to LLM provider: {_provider.name}")

    return _provider


def create_provider_with_fallback(config=None) -> Tuple[LLMProvider, List[str]]:
    """
    Create an LLM provider with automatic fallback.

    Tries providers in priority order:
    1. llama.cpp (local) - Primary, most reliable
    2. Ollama - Fallback for when local model fails

    Args:
        config: Optional Config object

    Returns:
        Tuple of (working provider, list of failed providers)

    Raises:
        ProviderError: If all providers fail
    """
    if config is None:
        from ..config import get_config

        config = get_config()

    errors: List[str] = []
    failed_providers: List[str] = []

    # Determine provider order based on config
    requested_provider = config.llm.provider
    if requested_provider in PROVIDER_PRIORITY:
        # Put requested provider first, then others
        provider_order = [requested_provider] + [p for p in PROVIDER_PRIORITY if p != requested_provider]
    else:
        provider_order = PROVIDER_PRIORITY

    for provider_type in provider_order:
        try:
            logger.info(f"Attempting to create provider: {provider_type}")
            provider = create_provider_from_config(config, provider_override=provider_type)

            # Try to load and verify the provider works
            provider.load()

            # Quick health check
            if provider.health_check():
                logger.info(f"✓ Provider {provider_type} loaded and healthy")
                return provider, failed_providers
            else:
                # Loaded but health check failed
                logger.warning(f"Provider {provider_type} loaded but health check failed")
                provider.unload()
                failed_providers.append(provider_type)
                errors.append(f"{provider_type}: health check failed")

        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Provider {provider_type} failed: {error_msg}")
            failed_providers.append(provider_type)
            errors.append(f"{provider_type}: {error_msg}")
            continue

    # All providers failed
    error_details = "\n  ".join(errors)
    raise ProviderError(
        f"All LLM providers failed:\n  {error_details}\n\n"
        f"Please ensure either:\n"
        f"  1. A GGUF model is available at the configured path\n"
        f"  2. Ollama is running (ollama serve) with a model pulled\n",
        provider="factory",
        retryable=False,
    )


def get_provider_with_fallback(config=None) -> LLMProvider:
    """
    Get a working LLM provider with automatic fallback.

    This is the recommended way to get a provider as it handles
    failures gracefully and tries alternatives.

    Args:
        config: Optional Config object

    Returns:
        Working LLMProvider instance
    """
    global _provider

    if _provider is None:
        _provider, failed = create_provider_with_fallback(config)
        if failed:
            logger.warning(f"Some providers failed: {', '.join(failed)}")

    return _provider
