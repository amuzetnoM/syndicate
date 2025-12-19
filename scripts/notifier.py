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

    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        logging.info("Sent alert to Discord webhook")
        return True
    except Exception as e:
        logging.exception("Failed to send Discord webhook: %s", e)
        return False
