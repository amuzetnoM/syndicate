import types
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from scripts.notion_publisher import NotionPublisher, NotionConfig


def test_publish_failure_sends_alert(monkeypatch):
    # Fake client that always fails
    class FakePages:
        def create(self, *a, **k):
            raise RuntimeError("boom")

    class FakeClient:
        def __init__(self, auth=None):
            self.pages = FakePages()
            self.databases = types.SimpleNamespace(query=lambda **k: {"results": []})
            self.request = lambda *a, **k: {"results": []}

    monkeypatch.setattr("scripts.notion_publisher.Client", FakeClient)

    sent = {}

    def fake_send(msg):
        sent['msg'] = msg
        return True

    monkeypatch.setattr("scripts.notifier.send_discord", fake_send)

    p = NotionPublisher(NotionConfig(api_key="x", database_id="db-x"))

    # Force _get_database_properties to a minimal schema
    monkeypatch.setattr(p, "_get_database_properties", lambda: {})

    with pytest.raises(Exception):
        p.publish(title="T", content="# T", use_enhanced_formatting=False)

    assert 'Notion publish failed' in sent['msg']
