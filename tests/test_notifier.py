import types

import pytest

from scripts.notifier import send_discord


def test_send_discord_success(monkeypatch):
    calls = {}

    class FakeResp:
        def raise_for_status(self):
            return None

    def fake_post(url, json=None, timeout=None):
        calls['url'] = url
        calls['json'] = json
        return FakeResp()

    monkeypatch.setattr('requests.post', fake_post)

    ok = send_discord('hello', webhook_url='https://discord.test/webhook')
    assert ok is True
    assert calls['url'] == 'https://discord.test/webhook'
    assert calls['json']['content'] == 'hello'


def test_send_discord_no_url(monkeypatch):
    # No requests.post available: ensure it returns False but doesn't raise
    monkeypatch.setattr('requests.post', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('fail')))
    ok = send_discord('x', webhook_url=None)
    assert ok is False
