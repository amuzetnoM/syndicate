#!/usr/bin/env python3
"""
Small test harness to validate that the Cortex class initializes `cortex_memory.json` from the template when missing.
This does not run the full suite; it's only a small functional check.
"""
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "cortex_memory.template.json"
TARGET = ROOT / "cortex_memory.json"

def cleanup():
    if TARGET.exists():
        print('Removing existing target for test...')
        TARGET.unlink()

def run_test():
    import sys
    sys.path.insert(0, str(ROOT))
    from main import Config, setup_logging, Cortex
    
    cfg = Config()
    log = setup_logging(cfg)
    print('Instantiating Cortex...')
    c = Cortex(cfg, log)
    print('Memory loaded keys:', list(c.memory.keys()))
    print('Memory file created:', TARGET.exists())
    if TARGET.exists():
        print('Size:', TARGET.stat().st_size)
    return 0

if __name__ == '__main__':
    cleanup()
    exit(run_test())
