#!/usr/bin/env python3
"""Premarket Watcher: ensures a pre-market plan exists for today and generates it if missing.
Runs as a simple long-lived agent (can be managed by systemd).
"""
import time
import datetime
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db_manager import get_db
from scripts.pre_market import generate_premarket
from main import Config, setup_logging

CHECK_INTERVAL = int(__import__("os").environ.get("PREMARKET_WATCH_INTERVAL", "300"))  # seconds


def main():
    config = Config()
    logger = setup_logging(config)
    logger.info("Starting premarket_watcher agent")

    while True:
        try:
            today = datetime.date.today().isoformat()
            db = get_db()
            if not db.has_premarket_for_date(today):
                logger.info(f"Premarket missing for {today} - generating now")
                try:
                    generate_premarket(config, logger, model=None, dry_run=False, no_ai=False)
                    logger.info("Premarket generation finished")
                    try:
                        db.set_premarket_generated(today)
                    except Exception:
                        # set_premarket_generated may not exist; it's best-effort
                        pass
                except Exception as e:
                    logger.error(f"Failed to generate premarket: {e}", exc_info=True)
            else:
                logger.debug(f"Premarket already exists for {today}")
        except Exception as e:
            logger.error(f"Watcher loop error: {e}", exc_info=True)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
