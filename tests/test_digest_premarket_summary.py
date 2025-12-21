import os
import sys
import types
import tempfile
from pathlib import Path

# Make repo importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Stub yfinance if missing
sys.modules.setdefault('yfinance', types.ModuleType('yfinance'))

from src.digest_bot.daily_report import build_report
from db_manager import DatabaseManager


def test_digest_includes_premarket(tmp_path, monkeypatch):
    # Create a fake premarket file
    reports = tmp_path / 'output' / 'reports'
    reports.mkdir(parents=True)
    pm = reports / 'premarket_2025-12-21.md'
    pm.write_text('''---\ntype: Pre-Market\ntitle: "Pre-Market Plan"\n---\n*   **Overall Bias:** **BULLISH** - Accumulate on Dips\n*   **Rationale:** Market is trending with momentum.\n''')

    # Insert a notion_sync entry
    db = DatabaseManager()
    with db._get_connection() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO notion_sync (file_path, file_hash, notion_page_id, notion_url, doc_type) VALUES (?, ?, ?, ?, ?)", (str(pm), 'h', 'pid', 'https://notion.test/page', 'Pre-Market'))
        conn.commit()

    # Monkeypatch the repository root resolution in the module by setting expected path
    monkeypatch.setenv('GOLD_STANDARD__BASE', str(tmp_path))

    # Build report
    r = build_report(db, hours=24)
    assert 'Pre-Market Summary' in r
    assert 'BULLISH' in r or 'BULLISH' in r
    assert 'Notion:' in r or 'https://notion.test/page' in r
