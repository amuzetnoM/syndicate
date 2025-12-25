#!/usr/bin/env python3
"""Create a Discord channel webhook using a Bot token.

Usage:
  DISCORD_BOT_TOKEN=<bot token> python scripts/create_discord_webhook.py --channel-id 1234567890

This script POSTs to the Discord API to create a webhook in the given channel
and prints the webhook URL. Requires the bot to have Manage Webhooks permission
in the target channel.
"""
from __future__ import annotations

import os
import argparse
import logging
import requests

LOG = logging.getLogger("create_discord_webhook")

API_BASE = "https://discord.com/api/v10"


def create_webhook(bot_token: str, channel_id: str, name: str = "syndicate-bot") -> str:
    url = f"{API_BASE}/channels/{channel_id}/webhooks"
    headers = {"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"}
    payload = {"name": name}
    r = requests.post(url, json=payload, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()
    # Webhook URL format: https://discord.com/api/webhooks/{id}/{token}
    return f"https://discord.com/api/webhooks/{data['id']}/{data['token']}"


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a Discord webhook for a channel")
    parser.add_argument("--channel-id", required=True, help="Target channel ID to create the webhook in")
    parser.add_argument("--name", default="syndicate-bot", help="Webhook name")
    args = parser.parse_args(argv)

    bot_token = os.getenv("DISCORD_BOT_TOKEN")
    if not bot_token:
        LOG.error("DISCORD_BOT_TOKEN not set in env")
        return 2

    try:
        url = create_webhook(bot_token, args.channel_id, name=args.name)
        print(url)
        return 0
    except Exception as e:
        LOG.exception("Failed to create webhook: %s", e)
        return 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(main())
