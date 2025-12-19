# Quick tests to ensure ADX fallback handles DataFrame-shaped columns and misaligned indices
import sys
from pathlib import Path

import pandas as pd

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from main import Config, QuantEngine, setup_logging


def test_adx_with_dataframe_columns():
    cfg = Config()
    logger = setup_logging(cfg)
    q = QuantEngine(cfg, logger)

    # Build a DataFrame where OHLC columns are DataFrames (duplicate columns name scenario)
    idx = pd.date_range("2020-01-01", periods=30, freq="D")

    # Simulate duplicated-named subframes by creating a DataFrame with MultiIndex columns
    # so that accessing df['High'] returns a DataFrame (multi-column High). This mimics
    # cases where the data source returns hierarchical columns.
    cols = [
        ("High", "h1"),
        ("High", "h2"),
        ("Low", "l1"),
        ("Low", "l2"),
        ("Close", "c1"),
        ("Close", "c2"),
        ("Open", "o"),
        ("Volume", "v"),
    ]
    midx = pd.MultiIndex.from_tuples(cols)
    multi_vals = []
    for i in range(30):
        # h1,h2, l1,l2, c1,c2, open, volume
        multi_vals.append([i + 1, i + 1, i, i, i, i, i, 1000])
    ohlc_wrapped = pd.DataFrame(multi_vals, index=idx, columns=midx)
    # after this, ohlc_wrapped['High'] is a DataFrame with two columns

    # Monkey patch yfinance.download to return this synthetic DF so _fetch runs the ADX logic
    import yfinance as yf

    orig_download = yf.download
    try:
        yf.download = lambda *a, **k: ohlc_wrapped
        df = q._fetch("TICK", "TICK")
        assert df is not None
        assert any("ADX" in c for c in df.columns)
    finally:
        yf.download = orig_download


def test_adx_with_misaligned_indices():
    cfg = Config()
    logger = setup_logging(cfg)
    q = QuantEngine(cfg, logger)

    idx1 = pd.date_range("2020-01-01", periods=30, freq="D")
    idx2 = pd.date_range("2020-01-02", periods=30, freq="D")  # shifted by one day
    baseA = pd.DataFrame(
        {
            "Open": pd.Series(range(30), index=idx1),
            "Close": pd.Series(range(30), index=idx1),
            "High": pd.Series(range(1, 31), index=idx1),
            "Low": pd.Series(range(0, 30), index=idx1),
            "Volume": pd.Series([1000] * 30, index=idx1),
        }
    )
    baseB = pd.DataFrame(
        {
            "Open": pd.Series(range(30), index=idx2),
            "Close": pd.Series(range(30), index=idx2),
            "High": pd.Series(range(1, 31), index=idx2),
            "Low": pd.Series(range(0, 30), index=idx2),
            "Volume": pd.Series([1000] * 30, index=idx2),
        }
    )

    # Merge such that High comes from baseB (misaligned index) and others from baseA
    mixed = pd.DataFrame(index=idx1)
    mixed["Open"] = baseA["Open"]
    mixed["Close"] = baseA["Close"]
    mixed["High"] = baseB["High"]
    mixed["Low"] = baseA["Low"]
    mixed["Volume"] = baseA["Volume"]

    # Monkey patch yfinance.download to return this synthetic DF so _fetch runs the ADX logic
    import yfinance as yf

    orig_download = yf.download
    try:
        yf.download = lambda *a, **k: mixed
        df = q._fetch("TICK", "TICK")
        assert df is not None
        assert any("ADX" in c for c in df.columns)
    finally:
        yf.download = orig_download
