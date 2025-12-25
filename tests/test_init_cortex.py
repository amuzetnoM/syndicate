#!/usr/bin/env python3
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
"""
Small test harness to validate that the Cortex class initializes `cortex_memory.json` from the template when missing.
This does not run the full suite; it's only a small functional check.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "cortex_memory.template.json"
TARGET = ROOT / "cortex_memory.json"


def cleanup():
    if TARGET.exists():
        print("Removing existing target for test...")
        TARGET.unlink()


def run_test():
    import sys

    sys.path.insert(0, str(ROOT))
    from main import Config, Cortex, setup_logging

    cfg = Config()
    log = setup_logging(cfg)
    print("Instantiating Cortex...")
    c = Cortex(cfg, log)
    print("Memory loaded keys:", list(c.memory.keys()))
    print("Memory file created:", TARGET.exists())
    if TARGET.exists():
        print("Size:", TARGET.stat().st_size)
    return 0


if __name__ == "__main__":
    cleanup()
    exit(run_test())
