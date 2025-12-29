#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════════════
#  Digest Bot - LLM Provider Abstraction
#  Copyright (c) 2025 SIRIUS Alpha
# ══════════════════════════════════════════════════════════════════════════════
"""
LLM provider abstraction layer.

Supports multiple backends with unified interface:
- llama.cpp (default): On-device GGUF inference
- Ollama: Local server-based inference

Provider Priority:
1. llama.cpp (local) - Primary, most reliable, no network
2. Ollama - Fallback when local model fails

Use get_provider_with_fallback() for robust provider creation.
"""

from .base import GenerationConfig, LLMProvider, LLMResponse, ProviderError
from .factory import (
    PROVIDER_PRIORITY,
    create_provider,
    create_provider_from_config,
    get_provider,
    get_provider_with_fallback,
    reset_provider,
    switch_provider,
)

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "GenerationConfig",
    "ProviderError",
    "create_provider",
    "create_provider_from_config",
    "get_provider",
    "get_provider_with_fallback",
    "reset_provider",
    "switch_provider",
    "PROVIDER_PRIORITY",
]
