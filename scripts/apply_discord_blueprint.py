#!/usr/bin/env python3
"""Apply the Discord ServerBlueprint using the bot and create ops webhook.

Usage:
  DISCORD_BOT_TOKEN=... python scripts/apply_discord_blueprint.py --guild-id 14520...

Behavior:
- Connects as the bot, fetches the specified guild (or first guild available), applies the ServerBlueprint (creates roles/categories/channels),
- Finds the digests channel (`📊-daily-digests`) and creates a webhook in it (requires Manage Webhooks permission),
- Writes `DISCORD_OPS_CHANNEL_ID` and `DISCORD_WEBHOOK_URL` to the `.env` file in the repo root.
"""
from __future__ import annotations

import os
import argparse
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

LOG = logging.getLogger("apply_discord_blueprint")

try:
    import discord
except Exception:
    discord = None

import sys
from pathlib import Path
# Ensure repo root on path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.digest_bot.discord.self_guide import SelfGuide, ServerBlueprint

API_BASE = "https://discord.com/api/v10"


def write_env_var(key: str, value: str, env_path: str = ".env") -> None:
    """Write or replace a key=value in the env file (simple, idempotent)."""
    path = os.path.abspath(env_path)
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(f"{key}={value}\n")
        return

    with open(path, "r") as f:
        lines = f.readlines()

    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(key + "="):
            lines[i] = f"{key}={value}\n"
            found = True
            break

    if not found:
        lines.append(f"{key}={value}\n")

    with open(path, "w") as f:
        f.writelines(lines)


async def run(guild_id: str | None = None):
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        LOG.error("DISCORD_BOT_TOKEN not set in environment")
        return 2

    if discord is None:
        LOG.error("discord.py not installed in this environment")
        return 2

    intents = discord.Intents.default()
    intents.guilds = True
    # Avoid privileged member intents unless explicitly enabled in the Developer Portal
    intents.members = False

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        LOG.info(f"Logged in as {client.user}")
        # Find guild
        target_guild = None
        if guild_id:
            target_guild = client.get_guild(int(guild_id))
        else:
            # pick first guild
            guilds = list(client.guilds)
            target_guild = guilds[0] if guilds else None

        if not target_guild:
            LOG.error("Could not find target guild; ensure bot is a member")
            await client.close()
            return

        LOG.info(f"Applying blueprint to guild: {target_guild.name} ({target_guild.id})")
        guide = SelfGuide(ServerBlueprint.default())
        report = await guide.apply_blueprint(target_guild)
        LOG.info(f"Blueprint applied: {report}")

        # Find digests channel
        dig_channel = discord.utils.get(target_guild.text_channels, name="📊-daily-digests")
        if not dig_channel:
            LOG.error("Could not find digests channel after blueprint application")
        else:
            # Create webhook for the digests channel
            wh = await dig_channel.create_webhook(name="syndicate-bot")
            webhook_url = f"https://discord.com/api/webhooks/{wh.id}/{wh.token}"
            LOG.info(f"Created webhook: {webhook_url}")

            write_env_var("DISCORD_OPS_CHANNEL_ID", str(dig_channel.id))
            write_env_var("DISCORD_WEBHOOK_URL", webhook_url)
            LOG.info("Updated .env with DISCORD_OPS_CHANNEL_ID and DISCORD_WEBHOOK_URL")

        await client.close()

    await client.start(token)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Apply Discord Server Blueprint and create ops webhook")
    parser.add_argument("--guild-id", help="Guild id to apply blueprint to (optional)", default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)
    return asyncio.run(run(guild_id=args.guild_id))


if __name__ == "__main__":
    raise SystemExit(main())
