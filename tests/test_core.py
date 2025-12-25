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

# Ensure project root is importable (so tests can import main directly)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import types

# Monkeypatch pandas_ta to avoid numba dependency in tests
fake_pandas_ta = types.SimpleNamespace(
    rsi=lambda series, length=14: [],
    sma=lambda series, length=50: [],
    atr=lambda high, low, close, length=14: [],
    adx=lambda high, low, close, length=14: None,
)
sys.modules["pandas_ta"] = fake_pandas_ta

from main import Config, Strategist, setup_logging


def test_extract_bias_explicit():
    cfg = Config()
    logger = setup_logging(cfg)
    data = {"GOLD": {"price": 2000, "atr": 5}, "VIX": {"price": 12}}
    s = Strategist(cfg, logger, data, [], "No history", model=None)

    txt = "**BIAS**: **BULLISH**\nSome other content"
    assert s._extract_bias(txt) == "BULLISH"

    txt2 = "Bias: BEARISH based on technicals"
    assert s._extract_bias(txt2) == "BEARISH"


def test_extract_bias_fallback_counts():
    cfg = Config()
    logger = setup_logging(cfg)
    data = {"GOLD": {"price": 2000, "atr": 5}}
    s = Strategist(cfg, logger, data, [], "No history", model=None)

    txt = "BULLISH repeated BULLISH BULLISH BEARISH"
    assert s._extract_bias(txt) == "BULLISH"

    txt2 = "Some text NEUTRAL but BEARISH BEARISH"
    assert s._extract_bias(txt2) == "BEARISH"
