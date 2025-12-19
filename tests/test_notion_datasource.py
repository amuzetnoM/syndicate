import json
import types
import sys
from pathlib import Path

# Ensure project root is on sys.path for test imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from scripts.notion_publisher import NotionPublisher, NotionConfig


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_discover_data_source_and_schema(monkeypatch):
    dbid = "db-abc"

    def fake_get(url, headers=None, timeout=None):
        if url.endswith(f"/databases/{dbid}"):
            return DummyResponse({"data_sources": [{"id": "ds-1", "name": "Main Source"}]})
        elif url.endswith("/data_sources/ds-1"):
            return DummyResponse({"properties": {"Status": {"type": "status"}, "Tags": {"type": "multi_select"}}})
        raise AssertionError(f"Unexpected url {url}")

    # Patch top-level requests.get so internal imports in the module resolve
    monkeypatch.setattr("requests.get", fake_get)

    p = NotionPublisher(NotionConfig(api_key="x", database_id=dbid))

    props = p._get_database_properties()
    assert p._data_source_id == "ds-1"
    assert props["Status"]["type"] == "status"
    assert props["Tags"]["type"] == "multi_select"


def test_publish_builds_properties_and_uses_data_source_parent(monkeypatch):
    # Prepare publisher with pre-populated data source id and properties
    cfg = NotionConfig(api_key="x", database_id="db-zzz")
    # Fake client to capture pages.create calls
    class FakePages:
        def __init__(self):
            self.last = None

        def create(self, parent=None, properties=None, children=None):
            self.last = {"parent": parent, "properties": properties, "children": children}
            return {"id": "page-1", "url": "https://notion.so/page-1"}

    class FakeClient:
        def __init__(self, auth=None):
            self.pages = FakePages()
            self.databases = types.SimpleNamespace(query=lambda **k: {"results": []})
            self.request = lambda *a, **k: {"results": []}

    monkeypatch.setattr("scripts.notion_publisher.Client", FakeClient)

    p = NotionPublisher(cfg)
    p._data_source_id = "ds-1"

    # Make _get_database_properties return a schema with various property types
    monkeypatch.setattr(p, "_get_database_properties", lambda: {
        "Status": {"type": "status"},
        "Tags": {"type": "multi_select"},
        "Date": {"type": "date"},
        "Type": {"type": "select"},
    })

    content = "---\nstatus: Published\ndate: 2025-12-19\ntags: [testing]\n---\n# Title\nBody"
    res = p.publish(title="Title", content=content, doc_type="reports", use_enhanced_formatting=False)

    # Assert pages.create was called and parent used data_source_id
    pages = p.client.pages
    assert pages.last is not None
    assert pages.last["parent"]["type"] == "data_source_id"
    assert pages.last["parent"]["data_source_id"] == "ds-1"

    props = pages.last["properties"]
    assert props["Status"]["status"]["name"] == "Published"
    assert props["Tags"]["multi_select"][0]["name"] == "testing"
    assert props["Date"]["date"]["start"] == "2025-12-19"
    assert props["Type"]["select"]["name"] == "reports"


def test_list_docs_uses_data_source_query(monkeypatch):
    cfg = NotionConfig(api_key="x", database_id="db-zzz")
    p = NotionPublisher(cfg)
    p._data_source_id = "ds-1"

    # Fake pages result
    page = {
        "id": "pg1",
        "properties": {
            "Name": {"title": [{"plain_text": "My Title"}]},
            "Type": {"select": {"name": "reports"}},
            "Date": {"date": {"start": "2025-12-01"}},
            "Tags": {"multi_select": [{"name": "T1"}]},
        },
    }

    def fake_request(method, path, json=None, headers=None):
        assert method == "POST"
        assert path.endswith("/data_sources/ds-1/query")
        return {"results": [page]}

    class FakeClient:
        def __init__(self, auth=None):
            self.request = fake_request
            self.databases = types.SimpleNamespace(query=lambda **k: {"results": []})

    # Monkeypatch Client before creating the publisher so the client.request binding is used
    monkeypatch.setattr("scripts.notion_publisher.Client", FakeClient)
    p = NotionPublisher(cfg)
    p._data_source_id = "ds-1"

    docs = p.list_docs(limit=1)
    assert len(docs) == 1
    assert docs[0]["title"] == "My Title"
    assert docs[0]["type"] == "reports"
    assert docs[0]["date"] == "2025-12-01"