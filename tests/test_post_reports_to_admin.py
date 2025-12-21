import json
from pathlib import Path

import pytest

import scripts.post_reports_to_admin as pr


def test_parse_frontmatter(tmp_path):
    p = tmp_path / "sample.md"
    content = """---\nname: Test\ngenerated: 2025-12-21T10:00:00\ntags: [Bullish]\n---\n# Hello\nBody text here\n"""
    p.write_text(content, encoding="utf-8")
    fm, body = pr.parse_frontmatter(p)
    assert fm.get("name") == "Test"
    assert "Hello" in body
    assert fm.get("generated")


def test_create_text_channel_if_missing_permission_overwrites(monkeypatch):
    calls = {}

    def fake_get(url, headers=None, timeout=None):
        class R:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return []

        return R()

    def fake_post(url, headers=None, json=None, timeout=None):
        calls['json'] = json

        class R:
            status_code = 201

            def json(self):
                return {"id": "9999"}

        return R()

    monkeypatch.setattr(pr.requests, 'get', fake_get)
    monkeypatch.setattr(pr.requests, 'post', fake_post)

    res = pr.create_text_channel_if_missing('token', 5555, 'test-channel', 'topic', publisher_role_ids=[111, 222])
    assert res == 9999
    payload = calls.get('json')
    assert payload is not None
    po = payload.get('permission_overwrites')
    assert isinstance(po, list)
    # first overwrite should be @everyone denial
    assert any(o for o in po if o.get('id') == '5555' and o.get('deny') == str(2048))
    # publisher roles allowed
    assert any(o for o in po if o.get('id') == '111' and o.get('allow') == str(2048))
