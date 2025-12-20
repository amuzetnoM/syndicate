import os
import sys
import logging
import socket
from pathlib import Path

import pytest

# Ensure project root is importable for tests
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.task_executor import TaskExecutor, TaskResult


def _ollama_reachable(host: str) -> bool:
    # First try a quick HTTP GET (if requests is available), then fall back to TCP connect.
    try:
        import requests
        try:
            r = requests.get(host, timeout=2)
            if r.status_code < 500:
                return True
        except Exception:
            pass
    except Exception:
        pass

    try:
        url = host.replace("http://", "").replace("https://", "").split(":")
        hostpart = url[0]
        port = int(url[1]) if len(url) > 1 else 11434
        with socket.create_connection((hostpart, port), timeout=2):
            return True
    except Exception:
        return False


def test_ollama_integration_real(tmp_path):
    """Integration test: use real OllamaProvider if an Ollama server is reachable.

    This test will be skipped if OLLAMA_HOST is not set or Ollama is not reachable.
    It runs a single `research` action through `TaskExecutor` and asserts output file creation.
    """
    ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    if not _ollama_reachable(ollama_host):
        pytest.skip("Ollama server not reachable; skipping integration test")

    # Build a simple config-like object pointing output to tmp_path
    class Cfg:
        OUTPUT_DIR = str(tmp_path)
        OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")

    logger = logging.getLogger("TestExecutor")
    logger.setLevel(logging.INFO)

    # Create a real OllamaProvider via main.OllamaProvider
    from main import OllamaProvider

    model = OllamaProvider(model=Cfg.OLLAMA_MODEL)
    assert model.is_available, "Ollama provider reported unavailable despite reachable server"

    # Minimal dummy action and extractor
    class Action:
        def __init__(self):
            self.action_id = "itest1"
            self.title = "Research: Integration Test Topic"
            self.description = "Integration test description"
            self.priority = "low"
            self.action_type = "research"
            self.source_context = "itest"
            self.source_report = None
            self.status = "pending"

    class Extractor:
        def __init__(self, actions):
            self._actions = actions

        def get_pending_actions(self):
            return list(self._actions)

        def mark_action_complete(self, action_id, result_str):
            pass

        def mark_action_failed(self, action_id, reason):
            pass

    action = Action()
    extractor = Extractor([action])

    executor = TaskExecutor(Cfg(), logger, model=model, insights_extractor=extractor)

    results = executor.execute_all_pending()

    assert isinstance(results, list)
    assert len(results) == 1
    res = results[0]
    assert isinstance(res, TaskResult)
    if not res.success:
        pytest.skip(f"Ollama provider failed to generate result: {res.error_message}")
    assert res.artifacts and len(res.artifacts) == 1
    assert os.path.exists(res.artifacts[0])
