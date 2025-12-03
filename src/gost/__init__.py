"""
Gold Standard (gost) - Autonomous Precious Metals Intelligence System

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

__version__ = "3.1.0"
__author__ = "amuzetnoM"
__license__ = "MIT"

from gost.core import GoldStandard
from gost.cli import main

__all__ = ["GoldStandard", "main", "__version__"]
