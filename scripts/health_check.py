#!/usr/bin/env python3
"""Run a quick health check for the environment.

Checks:
- Python version (must be 3.12)
- Required packages can be imported
- Notion connection (optional, if API key present)
- Database toggles (notion publishing enabled)
- Executor can be instantiated
"""
import sys
import importlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_PKGS = [
    "pandas",
    "numpy",
    "numba",
    "mplfinance",
    "yfinance",
    "notion_client",
]


def check_python_version():
    v = sys.version_info
    ok = (v.major == 3 and v.minor == 12)
    print(f"Python: {sys.version.splitlines()[0]} -> {'OK' if ok else 'WARN (expected 3.12)'}")
    return ok


def check_packages():
    missing = []
    for pkg in REQUIRED_PKGS:
        try:
            importlib.import_module(pkg)
            print(f"OK: import {pkg}")
        except Exception as e:
            print(f"MISSING: {pkg} ({e})")
            missing.append(pkg)
    return missing


def check_notion():
    from dotenv import load_dotenv

    try:
        from gold_standard.utils.env_loader import load_env

        load_env(PROJECT_ROOT / ".env")
    except Exception:
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except Exception:
            pass
    from os import getenv

    key = getenv("NOTION_API_KEY")
    dbid = getenv("NOTION_DATABASE_ID")
    if not key or not dbid:
        print("Notion: API keys not set (skipping connection test)")
        return False
    try:
        from scripts.notion_publisher import NotionPublisher

        p = NotionPublisher()
        # Try a lightweight fetch
        p.client.databases.retrieve(p.config.database_id)
        print("Notion: connection OK")
        return True
    except Exception as e:
        print(f"Notion: connection FAILED: {e}")
        return False


def check_db_toggles():
    try:
        from db_manager import get_db

        db = get_db()
        print(f"Notion publishing enabled: {db.is_notion_publishing_enabled()}")
        print(f"Task execution enabled: {db.is_task_execution_enabled()}")
        print(f"Insights extraction enabled: {db.is_insights_extraction_enabled()}")
        return True
    except Exception as e:
        print(f"DB check failed: {e}")
        return False


def check_executor():
    try:
        from scripts.executor_daemon import ExecutorDaemon, setup_logging
        import logging

        logger = setup_logging(verbose=True)
        ed = ExecutorDaemon(logger, dry_run=True)
        print("Executor: instantiated OK (dry-run)")
        return True
    except Exception as e:
        print(f"Executor: failed to instantiate: {e}")
        return False


def main():
    ok_py = check_python_version()
    missing = check_packages()
    notion_ok = check_notion()
    db_ok = check_db_toggles()
    exec_ok = check_executor()

    all_good = ok_py and (len(missing) == 0) and db_ok and exec_ok

    print("\nOverall health: {}".format("OK" if all_good else "ISSUES"))
    return 0 if all_good else 2


if __name__ == "__main__":
    raise SystemExit(main())
