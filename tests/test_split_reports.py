# ══════════════════════════════════════════════════════════════════════════════
#  _________._____________.___ ____ ___  _________      .__         .__
# /   _____/|   \______   \   |    |   \/   _____/____  |  | ______ |  |__ _____
# \_____  \ |   ||       _/   |    |   /\_____  \__  \ |  | \____ \|  |  \__  \
# /        \|   ||    |   \   |    |  / /        \/ __ \|  |_|  |_> >   Y  \/ __ \_
# /_______  /|___||____|_  /___|______/ /_______  (____  /____/   __/|___|  (____  /
#         \/             \/                     \/     \/     |__|        \/     \/
#
# Syndicate - Precious Metals Intelligence System
# Copyright (c) 2025 SIRIUS Alpha
# All rights reserved.
# ══════════════════════════════════════════════════════════════════════════════
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from main import Config, setup_logging
from scripts.split_reports import monthly_yearly_report, weekly_rundown


def test_weekly_rundown_no_ai():
    cfg = Config()
    logger = setup_logging(cfg)
    # Always run in no-ai mode to avoid external integrations in CI
    path = weekly_rundown(cfg, logger, model=None, dry_run=False, no_ai=True)
    assert path and os.path.exists(path)
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    assert "# Weekly Rundown" in text


def test_monthly_yearly_no_ai():
    cfg = Config()
    logger = setup_logging(cfg)
    path = monthly_yearly_report(cfg, logger, model=None, dry_run=False, no_ai=True)
    assert path and os.path.exists(path)
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    assert "# Monthly & Yearly Report" in text
