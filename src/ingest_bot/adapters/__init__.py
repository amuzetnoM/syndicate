"""Adapters package for Ingest Bot — contains source-specific adapters.

Each adapter should implement:
- fetch_since(timestamp: str) -> list[dict]
- sample_fixture.json for tests
"""
from . import fred, rapid, marketflow, tradingeconomics, yfinance_adapter
__all__ = ["fred", "rapid", "marketflow", "tradingeconomics", "yfinance_adapter"]
