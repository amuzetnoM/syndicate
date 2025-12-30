#!/usr/bin/env python3
"""
Discord Channel Cleanup Script
Removes duplicate/old-format channels from the Syndicate server.
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path

import discord

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ[key.strip()] = value.strip()

# Channels to DELETE (old format duplicates)
CHANNELS_TO_DELETE = [
    "🚨alerts",
    "daily_digests",
    "📈premarket_plans",
    "📔trading_journal",
    "📚research_journal",
    "📈day_charts",
    "💬discussion",
    "🎓resources",
    "📋serverline_commands",  # Replaced by 📋-bot-commands
]


async def cleanup_channels():
    intents = discord.Intents.default()
    intents.guilds = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print("=== Discord Channel Cleanup ===")
        print(f"Time: {datetime.now().isoformat()}")
        print(f"Bot: {client.user.name}")

        for guild in client.guilds:
            print(f"\nServer: {guild.name}")

            deleted_count = 0
            service_channel = None

            # Find service channel for logging
            for ch in guild.text_channels:
                if ch.name == "🔧-service":
                    service_channel = ch
                    break

            # Delete duplicate channels
            for ch in guild.text_channels:
                if ch.name in CHANNELS_TO_DELETE:
                    print(f"  Deleting: #{ch.name} (id: {ch.id})")
                    try:
                        await ch.delete(reason="Cleanup: Removing duplicate channel")
                        deleted_count += 1
                        print("    ✓ Deleted")
                    except discord.Forbidden:
                        print("    ✗ Permission denied")
                    except Exception as e:
                        print(f"    ✗ Error: {e}")

            # Log to service channel
            if service_channel:
                try:
                    embed = discord.Embed(
                        title="🧹 Channel Cleanup Complete",
                        description=f"Removed {deleted_count} duplicate channels",
                        color=0x2ECC71,
                        timestamp=datetime.utcnow(),
                    )
                    embed.add_field(
                        name="Removed",
                        value="\n".join(f"#{c}" for c in CHANNELS_TO_DELETE[:deleted_count]) or "None",
                        inline=False,
                    )
                    await service_channel.send(embed=embed)
                except Exception as e:
                    print(f"  Could not log to service channel: {e}")

            print(f"\n=== Cleanup Complete: {deleted_count} channels deleted ===")

        await client.close()

    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("ERROR: DISCORD_BOT_TOKEN not set")
        return

    await client.start(token)


if __name__ == "__main__":
    asyncio.run(cleanup_channels())
