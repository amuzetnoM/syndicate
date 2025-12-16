#!/usr/bin/env python3
"""Check LLM providers (Ollama then local) and run a quick generation test."""
import os
import logging
import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import Config, FallbackLLMProvider, setup_logging


def main():
    cfg = Config()
    logger = setup_logging(cfg)

    provider = FallbackLLMProvider(cfg, logger)
    print(f"Provider chain: {provider.name}")

    if not provider.is_available:
        print("No LLM providers available")
        return 2

    # Simple prompt
    prompt = "Write a 1-line concise market bias for GOLD."

    try:
        result = provider.generate_content(prompt)
        print("Generation OK:\n", getattr(result, "text", str(result)))
        return 0
    except Exception as e:
        print("Generation failed:", e)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())