"""Utility to load repository .env into process environment reliably.

This performs a best-effort parse of a .env file and sets variables into
os.environ so detached/spawned processes always see the same values.
"""
from pathlib import Path
import os
from typing import Iterable


def _parse_dotenv_lines(lines: Iterable[str]):
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        yield key, val


def load_env(path: str | Path = None, override: bool = False) -> None:
    """Load an .env file into os.environ.

    - `path`: path to .env (defaults to repo root .env).
    - `override`: if True, overwrite existing env vars.
    """
    root = Path(path) if path else Path(__file__).resolve().parents[2]
    dotenv = root / ".env"
    if not dotenv.exists():
        return

    try:
        with dotenv.open("r", encoding="utf-8") as fh:
            for k, v in _parse_dotenv_lines(fh):
                if k in os.environ and not override:
                    continue
                os.environ[k] = v
    except Exception:
        # Best-effort only; do not raise in production startup
        return
