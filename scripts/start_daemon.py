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
Start Syndicate daemon with AI enabled and configured interval.
This script uses the project's venv if present and runs run.py in background.
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_DIRS = ["venv312", "venv", ".venv"]


def find_venv_python():
    for v in VENV_DIRS:
        p = PROJECT_ROOT / v
        if p.exists():
            if sys.platform == "win32":
                exe = p / "Scripts" / "python.exe"
            else:
                exe = p / "bin" / "python"
            if exe.exists():
                return str(exe)
    return sys.executable


def start_daemon(interval_min=5):
    python = find_venv_python()
    cmd = [python, str(PROJECT_ROOT / "run.py"), "--interval-min", str(interval_min)]
    print("Starting daemon: ", " ".join(cmd))

    # Use detached Popen to keep background
    p = subprocess.Popen(cmd, cwd=str(PROJECT_ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(f"Process started with PID {p.pid}")


if __name__ == "__main__":
    start_daemon(5)
