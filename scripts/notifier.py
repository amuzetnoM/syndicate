#!/usr/bin/env python3
import os
import json
import logging
from typing import Optional

try:
    import requests
except ImportError:
    requests = None


def send_discord(message: str, webhook_url: Optional[str] = None) -> bool:
    """Send a simple message to a Discord webhook.

    Returns True on success, False on failure. Uses DISCORD_WEBHOOK_URL from
    environment when webhook_url is not provided.
    """
    url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
    if not url:
        logging.warning("No Discord webhook URL configured; skipping alert: %s", message)
        return False

    payload = {"content": message}

    if requests is None:
        logging.warning("requests not installed; cannot send webhook: %s", message)
        return False

    # Implement simple retries with exponential backoff
    import time
    attempts = 3
    delay = 1.0
    for attempt in range(1, attempts + 1):
        try:
            r = requests.post(url, json={"content": message}, timeout=10)
            if r.status_code in (200, 204):
                logging.info("Sent alert to Discord webhook (attempt %s)", attempt)
                return True
            logging.warning("Discord webhook returned HTTP %s on attempt %s: %s", r.status_code, attempt, r.text[:200])
        except Exception as e:
            logging.exception("Failed to send Discord webhook on attempt %s: %s", attempt, e)

        if attempt < attempts:
            time.sleep(delay)
            delay *= 2

    logging.error("Discord webhook failed after %s attempts", attempts)
    return False
