import os
from pathlib import Path

import pytest

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.digest_bot.discord.cogs.digest_workflow import ApproveView


import pytest

@pytest.mark.asyncio
async def test_approveview_instantiation():
    view = ApproveView(task_id=1, author_id=123)
    assert view is not None

@pytest.mark.skipif(not os.getenv("DISCORD_BOT_TOKEN"), reason="Live tests require a token")
def test_cmd_digest_full_live():
    # Live-only: requires bot token and operator role; skipped by default in CI
    pass
