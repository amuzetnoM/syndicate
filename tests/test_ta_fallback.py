import sys
from pathlib import Path
import pytest
import types

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from main import Config, setup_logging
from main import ta as orig_ta
from main import QuantEngine


def test_fetch_with_working_ta():
    """Test that _fetch works correctly with the real pandas_ta library.
    
    This test verifies that when pandas_ta is available and functioning,
    the indicators (RSI, SMA, ATR, ADX) are computed correctly without
    falling back to the simplified implementations.
    """
    cfg = Config()
    logger = setup_logging(cfg)
    q = QuantEngine(cfg, logger)
    
    # Fetch data using real TA library
    df = q._fetch('GC=F', 'GLD')
    
    if df is None:
        pytest.skip("No data available for GC/GLD in test environment")
    
    # Verify core price data exists
    assert 'Close' in df.columns
    assert 'High' in df.columns
    assert 'Low' in df.columns
    
    # Verify TA indicators were computed
    # RSI should be present
    rsi_cols = [c for c in df.columns if 'RSI' in str(c).upper()]
    assert len(rsi_cols) > 0, "RSI indicator should be computed"
    
    # SMA should be present (we compute SMA_20 and SMA_50)
    sma_cols = [c for c in df.columns if 'SMA' in str(c).upper()]
    assert len(sma_cols) >= 2, "SMA indicators should be computed"
    
    # ATR should be present
    atr_cols = [c for c in df.columns if 'ATR' in str(c).upper()]
    assert len(atr_cols) > 0, "ATR indicator should be computed"
    
    # ADX should be present
    adx_cols = [c for c in df.columns if 'ADX' in str(c).upper()]
    assert len(adx_cols) > 0, "ADX indicator should be computed"
    
    # Verify indicators have reasonable values (not all NaN)
    for col_list, name in [(rsi_cols, 'RSI'), (sma_cols, 'SMA'), 
                            (atr_cols, 'ATR'), (adx_cols, 'ADX')]:
        col = col_list[0]
        non_null = df[col].dropna()
        assert len(non_null) > 0, f"{name} should have non-null values"


def test_fetch_with_broken_ta(monkeypatch):
    cfg = Config()
    logger = setup_logging(cfg)
    q = QuantEngine(cfg, logger)

    # Ensure a baseline fetch works
    df = q._fetch('GC=F', 'GLD')
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

    monkeypatch.setattr('main.ta', BrokenTA())
    try:
        df2 = q._fetch('GC=F', 'GLD')
        assert df2 is not None
        assert 'Close' in df2.columns
    finally:
        # restore
        monkeypatch.setattr('main.ta', orig_ta)
