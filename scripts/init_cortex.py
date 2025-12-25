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
Initialize `cortex_memory.json` from the repository template if it doesn't already exist.
This is a small helper for new users who want a starting memory file in their local clone.

Usage:
  python scripts/init_cortex.py

"""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "cortex_memory.template.json"
TARGET = ROOT / "cortex_memory.json"


def init_cortex(force: bool = False):
    if TARGET.exists() and not force:
        print(f"Target {TARGET} already exists. Use --force to overwrite.")
        return 0
    if not TEMPLATE.exists():
        print(f"Template {TEMPLATE} not found. Nothing to do.")
        return 1
    shutil.copy2(str(TEMPLATE), str(TARGET))
    print(f"Copied template {TEMPLATE.name} -> {TARGET.name}")
    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Overwrite existing cortex file if present")
    args = parser.parse_args()
    raise SystemExit(init_cortex(force=args.force))
