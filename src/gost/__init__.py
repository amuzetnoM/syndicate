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
"""
Syndicate (gost) - Autonomous Precious Metals Intelligence System

A comprehensive end-to-end system combining real-time market data,
technical indicators, economic calendar intelligence, and Google Gemini AI
to generate structured trading reports for gold and intermarket assets.

Usage:
    pip install gost
    gost --help          # Show available commands
    gost                 # Start autonomous daemon
    gost --once          # Single analysis run
    gost --interactive   # Interactive menu
"""

__version__ = "3.4.0"
__author__ = "amuzetnoM"
__license__ = "MIT"

from gost.cli import main
from gost.core import GoldStandard

__all__ = ["GoldStandard", "main", "__version__"]
