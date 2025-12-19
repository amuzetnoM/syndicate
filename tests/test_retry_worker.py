import types
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.retry_failed_publishes import run_once


def test_run_once_skips_high_retry(monkeypatch, tmp_path):
    # Setup an in-memory DB with a pending document entry
    from db_manager import get_db

    # Create a fake row set to return: one file with retry_count 6 (should skip)
    class FakeCursor:
        def execute(self, q, *a, **k):
            pass

        def fetchall(self):
            return [{"file_path": "/tmp/f1.md", "retry_count": 6, "last_error": "x", "status": "failed"}]

    class FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr(get_db().__class__, "_get_connection", lambda self: FakeConn())

    called = {"sync": 0}

    class FakePublisher:
        def sync_file(self, *a, **kw):
            called["sync"] += 1

    monkeypatch.setattr("scripts.retry_failed_publishes.NotionPublisher", FakePublisher)

    run_once()
    assert called["sync"] == 0
