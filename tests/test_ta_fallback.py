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
import sys
from pathlib import Path

import pytest

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from main import Config, QuantEngine, setup_logging
from main import ta as orig_ta


def test_fetch_with_working_ta():
    """Test that _fetch works correctly with the real pandas_ta library.

    This test verifies that when pandas_ta is available and functioning,
    all core indicators (RSI, SMA, ATR, ADX) are computed correctly.
    The implementation has fallbacks for each indicator, so they should
    always be present regardless of pandas_ta availability.
    """
    cfg = Config()
    logger = setup_logging(cfg)
    q = QuantEngine(cfg, logger)

    # Fetch data using real TA library
    df = q._fetch("GC=F", "GLD")

    if df is None:
        pytest.skip("No data available for GC/GLD in test environment")

    # Verify core price data exists
    assert "Close" in df.columns
    assert "High" in df.columns
    assert "Low" in df.columns

    # Verify ALL TA indicators are computed (with fallbacks, they should always be present)

    # RSI should always be present (only needs 14 periods)
    rsi_cols = [c for c in df.columns if "RSI" in str(c).upper()]
    assert len(rsi_cols) > 0, f"RSI indicator should be computed, got columns: {list(df.columns)}"

    # SMA_50 and SMA_200 should be present (with fallback to pandas rolling)
    assert "SMA_50" in df.columns, f"SMA_50 should be computed, got columns: {list(df.columns)}"
    assert "SMA_200" in df.columns, f"SMA_200 should be computed, got columns: {list(df.columns)}"

    # ATR should always be present (only needs 14 periods)
    atr_cols = [c for c in df.columns if "ATR" in str(c).upper()]
    assert len(atr_cols) > 0, f"ATR indicator should be computed, got columns: {list(df.columns)}"

    # ADX should be present (ADX_14 from the code)
    adx_cols = [c for c in df.columns if "ADX" in str(c).upper()]
    assert len(adx_cols) > 0, f"ADX indicator should be computed, got columns: {list(df.columns)}"

    # Verify all indicators have reasonable values (not all NaN)
    for col, name in [("RSI", "RSI"), ("SMA_50", "SMA_50"), ("SMA_200", "SMA_200"), ("ATR", "ATR"), ("ADX_14", "ADX")]:
        if col in df.columns:
            non_null = df[col].dropna()
            assert len(non_null) > 0, f"{name} should have non-null values"

    # Verify SMA values are reasonable (between min and max Close prices)
    close_min, close_max = df["Close"].min(), df["Close"].max()
    sma50_values = df["SMA_50"].dropna()
    sma200_values = df["SMA_200"].dropna()

    assert sma50_values.min() >= close_min * 0.5, "SMA_50 values should be reasonable"
    assert sma50_values.max() <= close_max * 1.5, "SMA_50 values should be reasonable"
    assert sma200_values.min() >= close_min * 0.5, "SMA_200 values should be reasonable"
    assert sma200_values.max() <= close_max * 1.5, "SMA_200 values should be reasonable"


def test_fetch_with_broken_ta(monkeypatch):
    cfg = Config()
    logger = setup_logging(cfg)
    q = QuantEngine(cfg, logger)

    # Ensure a baseline fetch works
    df = q._fetch("GC=F", "GLD")
    if df is None:
        pytest.skip("No data available for GC/GLD in test environment")

    # Replace ta with a broken implementation to force fallback
    class BrokenTA:
        def rsi(self, *a, **k):
            raise RuntimeError("rsi crash")

        def sma(self, *a, **k):
            raise RuntimeError("sma crash")

        def atr(self, *a, **k):
            raise RuntimeError("atr crash")

        def adx(self, *a, **k):
            raise RuntimeError("adx crash")

    monkeypatch.setattr("main.ta", BrokenTA())
    try:
        df2 = q._fetch("GC=F", "GLD")
        assert df2 is not None
        assert "Close" in df2.columns
    finally:
        # restore
        monkeypatch.setattr("main.ta", orig_ta)
