import os
import sys
import types
import logging
from pathlib import Path

# Ensure project root is importable for tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Stub optional third-party modules
sys.modules.setdefault('yfinance', types.ModuleType('yfinance'))

from scripts.llm_worker import process_task
from main import Config


class DummyDB:
    def __init__(self):
        self.tasks = {}

    def update_llm_task_result(self, task_id, status, response=None, error=None, attempts=0):
        self.tasks[task_id] = dict(status=status, response=response, error=error, attempts=attempts)

    def save_llm_sanitizer_audit(self, task_id, corrections, notes):
        # Accept but do nothing (test only)
        self.tasks.setdefault(task_id, {})['audited'] = dict(corrections=corrections, notes=notes)


class DummyProvider:
    def __init__(self, text):
        self._text = text

    def generate_content(self, prompt: str):
        class R:
            text = self._text

        return R()


def test_llm_worker_sanitizes_plural_variants(monkeypatch, tmp_path):
    cfg = Config()
    cfg.BASE_DIR = str(tmp_path)

    # Prepare a prompt that includes canonical values for YIELD and DXY
    prompt = """
* DXY: $98.72
* YIELD: $4.15
"""

    # LLM returns content that wrongly repeats DXY for both mentions
    bad_text = "Gold is strong despite a firming DXY ($98.72) and rising Yields ($98.72)."

    # Create a temp file path for the document
    doc_path = str(tmp_path / "premarket_test.md")

    # Create a fake DB and provider
    monkeypatch.setattr('db_manager.get_db', lambda: DummyDB())
    # Patch the create_llm_provider _in the worker's module namespace_ so process_task uses our dummy
    import scripts.llm_worker as _lw
    monkeypatch.setattr(_lw, 'create_llm_provider', lambda cfg, log: DummyProvider(bad_text))

    task = {'id': 9999, 'document_path': doc_path, 'prompt': prompt, 'attempts': 0}

    # Run the worker processing for this single task
    process_task(task, cfg)

    # Validate the file exists and the Yields mention got corrected to $4.15
    content = Path(doc_path).read_text()
    assert 'Yields ($4.15)' in content or 'Yields ($4.15)' in content.replace('\n', ' ')
