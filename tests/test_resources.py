from __future__ import annotations

import pytest

try:
    from digest_bot.discord.cogs import resources
except Exception:
    import pytest

    pytest.skip("discord not available or digest_bot package not importable", allow_module_level=True)


class DummyBot:
    pass


def test_resources_cog_setup():
    cog = resources.ResourcesCog(DummyBot())
    assert hasattr(cog, "cmd_publish_changelog")
    assert hasattr(cog, "cmd_commands")
    assert hasattr(cog, "cmd_pin_commands")


@pytest.mark.parametrize("method", ["cmd_publish_changelog", "cmd_commands", "cmd_pin_commands"])
def test_methods_are_callables(method):
    cog = resources.ResourcesCog(DummyBot())
    func = getattr(cog, method)
    assert callable(func)
