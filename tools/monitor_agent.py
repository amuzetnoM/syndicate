#!/usr/bin/env python3
"""Simple log watcher for Syndicate.
Tails run_once.log and executor.log, scans for errors/warnings and writes alerts.
"""
import time
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
RUN_LOG = ROOT / "run_once.log"
EXEC_LOG = ROOT / "output" / "executor.log"
ALERT_LOG = ROOT / "output" / "monitor_alerts.log"

PATTERNS = [
    re.compile(r"\bERROR\b", re.I),
    re.compile(r"Exception", re.I),
    re.compile(r"Notion publish failed", re.I),
    re.compile(r"Notion publish succeeded", re.I),
    re.compile(r"Notion Published", re.I),
    re.compile(r"LLM\b", re.I),
    re.compile(r"Discord", re.I),
]


def tail_file(path: Path, last_pos: int):
    if not path.exists():
        return last_pos, []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        f.seek(last_pos)
        data = f.read()
        pos = f.tell()
    lines = data.splitlines()
    return pos, lines


def scan_lines(lines):
    alerts = []
    for line in lines:
        for p in PATTERNS:
            if p.search(line):
                alerts.append(line)
                break
    return alerts


def main():
    last_run = 0
    last_exec = 0
    ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
    ALERT_LOG.touch(exist_ok=True)

    with ALERT_LOG.open("a", encoding="utf-8") as out:
        out.write(f"=== Monitor started: {time.asctime()}\n")
        out.flush()

    try:
        while True:
            last_run, run_lines = tail_file(RUN_LOG, last_run)
            last_exec, exec_lines = tail_file(EXEC_LOG, last_exec)

            alerts = scan_lines(run_lines) + scan_lines(exec_lines)
            if alerts:
                ts = time.asctime()
                with ALERT_LOG.open("a", encoding="utf-8") as out:
                    for a in alerts:
                        out.write(f"[{ts}] {a}\n")
                    out.flush()
            time.sleep(2)
    except KeyboardInterrupt:
        print("Monitor stopped")


if __name__ == '__main__':
    main()
