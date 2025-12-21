import logging
import sys
import types
import os
from pathlib import Path

# Ensure project root is on sys.path and stub optional modules to make tests hermetic
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.modules.setdefault('yfinance', types.ModuleType('yfinance'))

from main import Config
from scripts.pre_market import generate_premarket


def test_premarket_enforces_canonical_prices(monkeypatch, tmp_path):
    # Prepare config
    config = Config()
    # Use tmp base dir so OUTPUT_DIR/CHARTS_DIR derive from it
    config.BASE_DIR = str(tmp_path)

    # Prepare data that QuantEngine.get_data should return
    fake_data = {
        'GOLD': {'price': 4387.3, 'rsi': 72.57, 'atr': 10.0},
        'SILVER': {'price': 67.49, 'rsi': 73.12, 'atr': 1.2},
        'DXY': {'price': 98.72},
        'YIELD': {'price': 4.15},
        'VIX': {'price': 14.91},
    }

    class DummyModel:
        def generate_content(self, prompt: str):
            class R:
                text = (
                    "Gold is strong despite a firming DXY ($98.72) and rising Yields ($98.72)."
                )

            return R()

    # Monkeypatch QuantEngine.get_data to return our fake data
    from main import QuantEngine

    monkeypatch.setattr(QuantEngine, 'get_data', lambda self: fake_data)

    # Ensure async queue is disabled in the test environment so generation is inline
    monkeypatch.delenv('LLM_ASYNC_QUEUE', raising=False)

    # Run generate_premarket with our dummy model
    logger = logging.getLogger('test')
    path = generate_premarket(config, logger, model=DummyModel(), dry_run=False, no_ai=False)

    content = Path(path).read_text()

    assert 'Yields ($4.15)' in content or 'Yields ($4.15)' in content.replace('\n', ' ')
    assert 'Yields ($98.72)' not in content
