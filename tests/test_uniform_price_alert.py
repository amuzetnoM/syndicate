import logging
import sys
import types
import os
from pathlib import Path

import pandas as pd

# Ensure project root is on sys.path and stub optional dependencies
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.modules.setdefault('yfinance', types.ModuleType('yfinance'))

from main import Config, QuantEngine


def test_uniform_price_triggers_discord_alert(monkeypatch, tmp_path):
    # Fake send_discord to capture calls
    sent = {}

    def fake_send(message: str, webhook_url=None):
        sent['message'] = message
        return True

    import scripts.notifier as notifier
    monkeypatch.setattr(notifier, 'send_discord', fake_send)

    # Minimal config
    config = Config()
    # Use a temp base dir so all derived paths point to tmp_path
    config.BASE_DIR = str(tmp_path)

    q = QuantEngine(config, logging.getLogger("test"))

    # Create a dummy DataFrame with identical close prices to trigger the diagnostic
    df = pd.DataFrame({'Close': [100.0, 100.0], 'RSI': [50, 50], 'ADX_14': [10, 10], 'ATR': [1, 1], 'SMA_200': [100, 100]})

    # Monkeypatch _fetch to return the same df for every asset
    monkeypatch.setattr(QuantEngine, '_fetch', lambda self, p, b: df)

    q.get_data()

    assert 'Uniform prices detected' in sent.get('message', '')
