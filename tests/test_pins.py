from __future__ import annotations

import pytest

try:
    from digest_bot.discord.cogs import pins
except Exception:
    import pytest

    pytest.skip("discord not available or digest_bot package not importable", allow_module_level=True)


class DummyBot:
    pass


def test_pins_cog_setup():
    cog = pins.PinsCog(DummyBot())
    assert hasattr(cog, "cmd_pin_latest")
    assert hasattr(cog, "cmd_pin_daily_charts")


@pytest.mark.parametrize("method", ["cmd_pin_latest", "cmd_pin_daily_charts"])
def test_methods_are_callables(method):
    cog = pins.PinsCog(DummyBot())
    func = getattr(cog, method)
    assert callable(func)
