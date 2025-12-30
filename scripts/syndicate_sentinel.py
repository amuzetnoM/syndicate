#!/usr/bin/env python3
"""
Syndicate Sentinel - Autonomous Infrastructure Watchdog
Protects the Syndicate VM from service failures, stuck tasks, and reboots.
"""

import logging
import os
import sqlite3
import subprocess
import time
from datetime import datetime, timedelta

# Configuration
SERVICES = ["syndicate-daemon.service", "syndicate-executor.service", "syndicate-discord.service"]

DB_PATH = os.path.expanduser("~/syndicate/data/syndicate.db")
CHECK_INTERVAL_SEC = 60
STUCK_TASK_MINUTES = 60

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] sentinel: %(message)s",
    handlers=[logging.FileHandler(os.path.expanduser("~/sentinel.log")), logging.StreamHandler()],
)
logger = logging.getLogger("sentinel")


def check_service(service_name: str) -> bool:
    """Check if a systemd service is active."""
    try:
        result = subprocess.run(["sudo", "systemctl", "is-active", service_name], capture_output=True, text=True)
        return result.stdout.strip() == "active"
    except Exception as e:
        logger.error(f"Failed to check service {service_name}: {e}")
        return False


def restart_service(service_name: str):
    """Restart a systemd service."""
    logger.warning(f"Attempting to restart {service_name}...")
    try:
        subprocess.run(["sudo", "systemctl", "restart", service_name], check=True)
        logger.info(f"✓ {service_name} restarted successfully.")
    except Exception as e:
        logger.error(f"Failed to restart {service_name}: {e}")


def reset_stuck_tasks():
    """Reset tasks that have been in_progress for too long."""
    if not os.path.exists(DB_PATH):
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Calculate threshold
        threshold = (datetime.now() - timedelta(minutes=STUCK_TASK_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            "UPDATE llm_tasks SET status='pending', last_attempt_at=CURRENT_TIMESTAMP WHERE status='in_progress' AND last_attempt_at < ?",
            (threshold,),
        )

        if cursor.rowcount > 0:
            logger.info(f"↺ Reset {cursor.rowcount} stuck tasks in database.")
            conn.commit()

        conn.close()
    except Exception as e:
        logger.error(f"Database recovery failed: {e}")


def health_check():
    """Main health check loop."""
    logger.info("Starting Sentinel health check cycle...")

    # 1. Check Services
    for service in SERVICES:
        if not check_service(service):
            logger.warning(f"🚨 Service {service} is DOWN!")
            restart_service(service)
        else:
            logger.info(f"✓ Service {service} is active.")

    # 2. Check Database
    reset_stuck_tasks()

    # 3. Resource Monitor (Placeholder for future Discord reporting)
    try:
        mem_info = subprocess.run(["free", "-m"], capture_output=True, text=True).stdout
        logger.info(f"Memory Snapshot:\n{mem_info}")
    except Exception as e:
        logger.debug(f"Resource monitor failed: {e}")


def main():
    logger.info("=== Syndicate Sentinel Activated ===")
    logger.info(f"Monitoring: {', '.join(SERVICES)}")

    while True:
        try:
            health_check()
        except KeyboardInterrupt:
            logger.info("Sentinel shutting down.")
            break
        except Exception as e:
            logger.error(f"Sentinel loop error: {e}")

        time.sleep(CHECK_INTERVAL_SEC)


if __name__ == "__main__":
    main()
