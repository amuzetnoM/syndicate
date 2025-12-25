#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════════════
#  Digest Bot - Syndicate Daily Summarizer
#  Copyright (c) 2025 SIRIUS Alpha
# ══════════════════════════════════════════════════════════════════════════════
"""
Digest Bot: Lightweight local-AI summarizer for Syndicate daily outputs.

Reads pre-market plans, daily journals, and weekly reports to generate
concise, actionable daily digests using local LLM inference.

Usage:
    python -m digest_bot run
    python -m digest_bot run --dry-run
    python -m digest_bot run --wait
    python -m digest_bot check
"""

__version__ = "1.0.0"
__author__ = "SIRIUS Alpha"

from .config import Config, get_config
from .file_gate import Document, FileGate, GateStatus
from .summarizer import DigestResult, Summarizer
from .writer import DigestWriter, WriteResult

__all__ = [
    # Version
    "__version__",
    "__author__",
    # Config
    "Config",
    "get_config",
    # File Gate
    "FileGate",
    "Document",
    "GateStatus",
    # Summarizer
    "Summarizer",
    "DigestResult",
    # Writer
    "DigestWriter",
    "WriteResult",
]
