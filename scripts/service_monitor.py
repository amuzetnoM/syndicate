#!/usr/bin/env python3
from __future__ import annotations
import time
import subprocess
import logging
import os

SERVICE_LIST = [
    "syndicate-discord-bot.service",
    "syndicate-llm-worker.service",
    "syndicate-daily-llm-report.timer",
]
CHECK_INTERVAL = int(os.getenv("GOLDSTANDARD_MONITOR_INTERVAL", "60"))
LOG_PATH = "/var/log/syndicate/service_monitor.log"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("syndicate.monitor")

# Ensure log directory exists
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
file_handler = logging.FileHandler(LOG_PATH)
file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(file_handler)


def is_active(unit: str) -> bool:
    r = subprocess.run(["systemctl", "is-active", unit], capture_output=True, text=True)
    return r.returncode == 0


def is_enabled(unit: str) -> bool:
    r = subprocess.run(["systemctl", "is-enabled", unit], capture_output=True, text=True)
    return r.returncode == 0


def restart_unit(unit: str) -> None:
    logger.warning("Restarting unit: %s", unit)
    subprocess.run(["systemctl", "restart", unit])


def enable_unit(unit: str) -> None:
    logger.info("Enabling unit: %s", unit)
    subprocess.run(["systemctl", "enable", unit])


if __name__ == "__main__":
    logger.info("Syndicate service monitor starting (interval=%s)" % CHECK_INTERVAL)

    while True:
        try:
            for unit in SERVICE_LIST:
                try:
                    active = is_active(unit)
                    if not active:
                        logger.error("Unit %s is not active; attempting restart", unit)
                        restart_unit(unit)
                    # Ensure units are enabled for boot
                    if not is_enabled(unit):
                        enable_unit(unit)
                except Exception as e:
                    logger.exception("Error while checking unit %s: %s", unit, e)
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Shutting down service monitor")
            raise
        except Exception:
            logger.exception("Unexpected monitor error; sleeping and continuing")
            time.sleep(CHECK_INTERVAL)
