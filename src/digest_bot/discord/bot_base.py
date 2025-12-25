"""Blueprint bot core for Syndicate Discord integration.

This module creates a `SyndicateBot` abstraction around `discord.Bot` to make
unit-testing and lifecycle management easier.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

# Import is lazy to avoid requiring discord in unit tests that don't need it
try:
    import discord
    from discord.ext import commands, tasks
except Exception:  # pragma: no cover - handled in tests via mock
    discord = None
    commands = None
    tasks = None

LOG = logging.getLogger("digest_bot.discord.bot_base")

DEFAULT_INTENTS = None


class GoldStandardBot:
    """Encapsulates Discord bot lifecycle and wiring.

    Core responsibilities:
    - Create and configure the discord client
    - Register cogs
    - Start background tasks (daily reporting / sanitizer watcher)
    - Expose graceful shutdown hooks
    """

    def __init__(self, token: Optional[str] = None, *, intents=None, prefix="!"):
        self.token = token or os.getenv("DISCORD_BOT_TOKEN")
        self.intents = intents or DEFAULT_INTENTS
        self.prefix = prefix
        self._bot = None
        self._tasks_started = False

    def _ensure_client(self):
        if self._bot is not None:
            return
        if discord is None or commands is None:
            raise RuntimeError("discord.py not available; install 'discord.py' to run the bot")
        intents = self.intents or discord.Intents.default()
        # Keep MESSAGE_CONTENT disabled unless explicitly enabled in env
        if os.getenv("DISCORD_ENABLE_MESSAGE_CONTENT") == "1":
            intents.message_content = True
        self._bot = commands.Bot(command_prefix=self.prefix, intents=intents)

        @self._bot.event
        async def on_ready():
            LOG.info("Discord bot ready as %s#%s", self._bot.user.name, self._bot.user.discriminator)

    def register_cog(self, cog):
        self._ensure_client()
        self._bot.add_cog(cog)

    def register_cogs(self, cogs: list):
        self._ensure_client()
        for c in cogs:
            self.register_cog(c)

    def start_background_cogs(self):
        # Register alerting and subscriptions cogs by default when running in real bot
        try:
            from .cogs import alerting, subscriptions
            self.register_cog(alerting.AlertingCog(self))
            self.register_cog(subscriptions.SubscriptionsCog(self))
        except Exception:
            LOG.exception("Failed to register background cogs")

    async def start(self):
        self._ensure_client()
        if not self.token:
            raise RuntimeError("DISCORD_BOT_TOKEN not provided")
        LOG.info("Starting GoldStandardBot");
        await self._bot.start(self.token)

    async def stop(self):
        if self._bot and self._bot.is_running():
            await self._bot.close()

    def run(self):
        # Convenience blocking runner
        self._ensure_client()
        if not self.token:
            raise RuntimeError("DISCORD_BOT_TOKEN not provided")
        try:
            self._bot.run(self.token)
        except KeyboardInterrupt:
            LOG.info("KeyboardInterrupt received, shutting down bot")


# Simple CLI-style entrypoint for development/testing
def main():
    token = os.getenv("DISCORD_BOT_TOKEN")
    bot = GoldStandardBot(token=token)
    # In dev, load cogs from the local package
    try:
        import importlib
        from .cogs import reporting, digest_workflow
        bot.register_cog(reporting.ReportingCog(bot))
        bot.register_cog(digest_workflow.DigestWorkflowCog(bot))
        # Also register background cogs
        bot.start_background_cogs()
    except Exception:
        LOG.exception("Failed to load development cogs")
