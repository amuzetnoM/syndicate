#!/usr/bin/env python3
from __future__ import annotations

# ══════════════════════════════════════════════════════════════════════════════
#  Digest Bot - Discord Bot Core
#  Copyright (c) 2025 SIRIUS Alpha
# ══════════════════════════════════════════════════════════════════════════════
"""
Discord bot with self-healing and self-guiding capabilities.

Features:
- Auto-reconnect with exponential backoff
- Self-healing error recovery
- Auto-create channels/roles based on bot's purpose
- Digest posting and management
- Health monitoring and status reporting
- Full Discord Server management including channel and role creation
"""

import asyncio
import logging
import os
import sys
from datetime import date, datetime
from typing import Any, Dict, Optional

try:
    import discord
    from discord import app_commands
    from discord.ext import commands, tasks

    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    discord = None
    # Provide minimal placeholders so modules importing this file do not fail during test collection
    commands = None

    class _DummyTasks:
        """Fallback tasks helper providing a compatible `loop` decorator and loop object."""

        class _DummyLoop:
            def __init__(self, fn):
                self.fn = fn

            def before_loop(self, coro):
                def decorator(f):
                    return f

                return decorator

            def start(self, *args, **kwargs):
                return None

            def cancel(self, *args, **kwargs):
                return None

        def loop(self, *args, **kwargs):
            def decorator(fn):
                return _DummyTasks._DummyLoop(fn)

            return decorator

        def start(self, *args, **kwargs):
            return None

    tasks = _DummyTasks()

# Determine a safe base class to inherit from for environments where discord.py is unavailable
if DISCORD_AVAILABLE and getattr(commands, "Bot", None):
    BotBase = commands.Bot
else:

    class _DummyBot:
        """Fallback base class used when discord.py is not installed. Allows importing without raising at module import time."""

        def __init__(self, *args, **kwargs):
            pass

    BotBase = _DummyBot

from ..config import Config, get_config
from .content_router import ContentType, detect_content_type, get_router
from .self_guide import SelfGuide, ServerBlueprint
from .self_healer import HealthState, SelfHealer

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# BOT IDENTITY & PURPOSE
# ══════════════════════════════════════════════════════════════════════════════

BOT_IDENTITY = """
I am the Syndicate Digest Bot, an AI-powered market intelligence assistant.

My Purpose:
- Generate and deliver daily market intelligence digests
- Synthesize pre-market plans, trading journals, and weekly reports
- Provide actionable insights using local LLM inference
- Maintain a healthy, organized Discord community structure

My Capabilities:
- 📊 Automated daily digest generation and posting
- 🔄 Self-healing: auto-reconnect, error recovery, circuit breakers
- 🏗️ Self-guiding: auto-create channels, roles, and server structure
- 📈 Health monitoring with status reporting
- 🔗 Server invite generation

My Values:
- Reliability: Always available, always recovering
- Clarity: Concise, actionable market intelligence
- Autonomy: Self-managing with minimal intervention needed
- Transparency: Clear logging and health status
"""


# ══════════════════════════════════════════════════════════════════════════════
# DISCORD BOT CLASS
# ══════════════════════════════════════════════════════════════════════════════


class DigestDiscordBot(BotBase):
    """
    Self-healing, self-guiding Discord bot for market digests.

    Combines:
    - discord.py Bot functionality
    - Self-healing capabilities (reconnect, recovery)
    - Self-guiding capabilities (channel/role creation)
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        blueprint: Optional[ServerBlueprint] = None,
    ):
        """
        Initialize the Digest Discord Bot.

        Args:
            config: Bot configuration
            blueprint: Server structure blueprint
        """
        if not DISCORD_AVAILABLE:
            raise ImportError("discord.py is not installed. " "Install with: pip install discord.py")

        # Intents for full functionality
        intents = discord.Intents.default()
        # Enable message content only if explicitly requested via env var
        if os.getenv("DISCORD_ENABLE_MESSAGE_CONTENT") == "1":
            intents.message_content = True
        # Members intent is privileged; enable only when allowed in portal
        if os.getenv("DISCORD_ENABLE_MEMBERS") == "1":
            intents.members = True
        intents.guilds = True

        super().__init__(
            command_prefix="!digest ",
            intents=intents,
            description=BOT_IDENTITY,
        )

        # Configuration
        self.config = config or get_config()

        # Self-healing
        self.healer = SelfHealer()

        # Self-guiding
        self.guide = SelfGuide(blueprint)

        # State
        self._ready = asyncio.Event()
        self._guild: Optional[discord.Guild] = None
        self._digest_channel: Optional[discord.TextChannel] = None
        self._log_channel: Optional[discord.TextChannel] = None

        # Content Routing
        self.router = get_router()

        # Setup tracking
        self._setup_complete = False
        self._last_digest_date: Optional[date] = None

    @property
    def _bot(self) -> DigestDiscordBot:
        """Compatibility property for cogs using self.bot._bot"""
        return self

    # ══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE EVENTS
    # ══════════════════════════════════════════════════════════════════════════

    async def setup_hook(self) -> None:
        """Called when the bot is starting up."""
        logger.info("Setting up bot...")

        # Add cogs/commands
        await self._register_commands()

        # Register recommended cogs (reporting, alerts, moderation, pins, etc.)
        try:
            from .cogs import (
                alerting,
                digest_workflow,
                intelligence,
                moderation,
                pins,
                reporting,
                resources,
                sanitizer_alerts,
                status,
                subscriptions,
            )

            # Add cogs idempotently to avoid duplicate command registration on reconnect
            cogs_to_add = [
                reporting.ReportingCog,
                digest_workflow.DigestWorkflowCog,
                sanitizer_alerts.SanitizerAlertsCog,
                moderation.ModerationCog,
                alerting.AlertingCog,
                subscriptions.SubscriptionsCog,
                pins.PinsCog,
                resources.ResourcesCog,
                status.Status,
                intelligence.IntelligenceCog,
            ]

            for cog_cls in cogs_to_add:
                try:
                    if not self.get_cog(cog_cls.__name__):
                        await self.add_cog(cog_cls(self))
                except Exception:
                    logger.exception("Failed to add cog %s", cog_cls.__name__)

        except Exception:
            logger.exception("Failed to register cogs")

        # Start background tasks
        self.digest_check_loop.start()
        self.health_report_loop.start()

    async def on_ready(self) -> None:
        """Called when the bot is fully connected."""
        logger.info(f"Bot connected as {self.user}")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")

        # Record successful connection
        self.healer.health.record_heartbeat()
        self.healer.reset_backoff()

        # Find and cache target guild
        if self.config.discord.guild_id:
            self._guild = self.get_guild(self.config.discord.guild_id)
        elif self.guilds:
            self._guild = self.guilds[0]

        if self._guild:
            logger.info(f"Operating in guild: {self._guild.name}")
            await self._ensure_server_setup()
        else:
            logger.warning("No guild found!")

        # Sync commands
        try:
            if self._guild:
                synced = await self.tree.sync(guild=self._guild)
                logger.info(f"Synced {len(synced)} commands to guild")
            else:
                synced = await self.tree.sync()
                logger.info(f"Synced {len(synced)} commands globally")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

        # Signal ready
        self._ready.set()

        # Log startup message
        await self._log_to_channel(
            "🟢 **Bot Online**\n"
            f"```\n"
            f"Version: 1.0.0\n"
            f"Guild: {self._guild.name if self._guild else 'None'}\n"
            f"Latency: {self.latency*1000:.0f}ms\n"
            f"```"
        )

    async def on_disconnect(self) -> None:
        """Called when the bot disconnects."""
        logger.warning("Bot disconnected!")
        self.healer.health.record_error("Disconnected from Discord")
        self._ready.clear()

    async def on_resumed(self) -> None:
        """Called when the bot resumes a session."""
        logger.info("Bot resumed session")
        self.healer.health.record_heartbeat()
        self._ready.set()

    async def on_error(self, event: str, *args, **kwargs) -> None:
        """Global error handler."""
        import traceback

        error = traceback.format_exc()

        logger.error(f"Error in {event}: {error}")
        self.healer.health.record_error(f"Event error: {event}")

        # Log to Discord
        await self._log_to_channel(f"⚠️ **Error in {event}**\n" f"```\n{error[:1500]}\n```")

    # ══════════════════════════════════════════════════════════════════════════
    # SELF-GUIDING: SERVER SETUP
    # ══════════════════════════════════════════════════════════════════════════

    async def _ensure_server_setup(self) -> None:
        """Ensure server has required structure."""
        if not self._guild:
            return

        if self._setup_complete:
            return

        logger.info("Checking server structure...")

        # Analyze current state
        analysis = await self.guide.analyze_server(self._guild)

        if analysis["needs_setup"]:
            logger.info("Server needs setup, applying blueprint...")

            # Apply blueprint
            report = await self.guide.apply_blueprint(self._guild)

            if report["errors"]:
                for error in report["errors"]:
                    logger.warning(f"Setup error: {error}")

            logger.info(
                f"Setup complete: "
                f"{len(report['roles_created'])} roles, "
                f"{len(report['categories_created'])} categories, "
                f"{len(report['channels_created'])} channels"
            )
        else:
            logger.info("Server structure is complete")

        # Cache channels
        await self._cache_channels()

        self._setup_complete = True

    async def _cache_channels(self) -> None:
        """
        Cache important channels.

        Note: We primarily use the content router now, but some legacy
        code may still rely on these cached attributes.
        """
        if not self._guild:
            return

        # Use router to find channels
        self._digest_channel = await self.router.get_channel(self._guild, ContentType.DIGEST)
        self._log_channel = await self.router.get_channel(self._guild, ContentType.BOT_LOG)
        self._reports_channel = await self.router.get_channel(self._guild, ContentType.SYSTEM_REPORT)
        self._commands_codex_channel = await self.router.get_channel(self._guild, ContentType.BOT_COMMAND)

        logger.info("Cached channels via router.")

    # ══════════════════════════════════════════════════════════════════════════
    # MESSAGING
    # ══════════════════════════════════════════════════════════════════════════

    async def _log_to_channel(self, message: str) -> None:
        """Send log message to bot logs channel (via router)."""
        if not self._guild:
            return

        channel = await self.router.get_channel(self._guild, ContentType.BOT_LOG)
        if channel:
            try:
                await channel.send(message)
                self.router.mark_channel_healthy(channel.name)
            except Exception as e:
                logger.error(f"Failed to log to channel: {e}")
                self.router.mark_channel_unhealthy(channel.name)

    async def post_digest(
        self,
        content: str,
        embed: Optional[discord.Embed] = None,
    ) -> Optional[discord.Message]:
        """
        Post a digest to the digests channel.
        """
        return await self.post_content(content=content, embed=embed, content_type=ContentType.DIGEST)

    async def post_content(
        self,
        content: str,
        embed: Optional[discord.Embed] = None,
        content_type: Optional[ContentType] = None,
        filename: Optional[str] = None,
        doc_type: Optional[str] = None,
        attachments: Optional[list] = None,
    ) -> Optional[discord.Message]:
        """
        Post content to the appropriate channel using the router.

        Detects content type if not provided.
        """
        if not self._guild:
            logger.warning("No guild available for posting")
            return None

        # Detect content type if not provided
        if not content_type:
            content_type = detect_content_type(filename=filename, doc_type=doc_type, content=content)
            logger.info("Detected content type: %s", content_type.name)

        # Get channel from router
        channel = await self.router.get_channel(self._guild, content_type)
        if not channel:
            logger.warning("No channel found for content type: %s", content_type.name)
            return None

        try:
            files = []
            if attachments:
                for path in attachments:
                    try:
                        files.append(discord.File(path))
                    except Exception as e:
                        logger.warning(f"Failed to attach file {path}: {e}")

            if embed:
                msg = await channel.send(content, embed=embed, files=files or None)
            else:
                msg = await channel.send(content, files=files or None)

            logger.info(f"Posted {content_type.name} to {channel.name}")
            self.router.mark_channel_healthy(channel.name)
            return msg

        except Exception as e:
            logger.error(f"Failed to post {content_type.name}: {e}")
            self.healer.health.record_error(f"{content_type.name} post failed: {e}")
            self.router.mark_channel_unhealthy(channel.name)
            return None

    async def post_report(
        self,
        title: str,
        content: str,
        embed: Optional[discord.Embed] = None,
        attachments: Optional[list] = None,
    ) -> Optional[discord.Message]:
        """
        Post an administrative report to the reports channel (admin inbox).
        """
        body = f"**{title}**\n{content}"
        return await self.post_content(
            content=body, embed=embed, content_type=ContentType.SYSTEM_REPORT, attachments=attachments
        )

    def create_digest_embed(
        self,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> discord.Embed:
        """
        Create a rich embed for a digest.

        Args:
            title: Embed title
            content: Main content
            metadata: Generation metadata

        Returns:
            Discord Embed
        """
        embed = discord.Embed(
            title=title,
            description=content[:4000],  # Discord limit
            color=discord.Color.gold(),
            timestamp=datetime.now(),
        )

        embed.set_author(
            name="Syndicate Digest Bot",
            icon_url=self.user.avatar.url if self.user and self.user.avatar else None,
        )

        if metadata:
            embed.add_field(
                name="📊 Generation Info",
                value=(
                    f"Provider: {metadata.get('provider', 'N/A')}\n"
                    f"Model: {metadata.get('model', 'N/A')}\n"
                    f"Tokens: {metadata.get('tokens_used', 'N/A')}"
                ),
                inline=True,
            )

        embed.set_footer(text="Generated by local AI • Not financial advice")

        return embed

    # ══════════════════════════════════════════════════════════════════════════
    # INVITE GENERATION
    # ══════════════════════════════════════════════════════════════════════════

    async def create_invite(
        self,
        max_age: int = 86400,
        max_uses: int = 0,
    ) -> Optional[str]:
        """
        Create a server invite.

        Args:
            max_age: Expiry in seconds (0 = never)
            max_uses: Max uses (0 = unlimited)

        Returns:
            Invite URL or None
        """
        # Use a suitable channel
        channel = self._digest_channel or (self._guild.text_channels[0] if self._guild else None)

        if not channel:
            logger.error("No channel available for invite")
            return None

        return await self.guide.create_invite(
            channel,
            max_age=max_age,
            max_uses=max_uses,
        )

    # ══════════════════════════════════════════════════════════════════════════
    # BACKGROUND TASKS
    # ══════════════════════════════════════════════════════════════════════════

    @tasks.loop(minutes=30)
    async def digest_check_loop(self) -> None:
        """Periodically check if digest needs to be generated."""
        await self._ready.wait()

        today = date.today()

        # Skip if already posted today
        if self._last_digest_date == today:
            return

        logger.info("Checking for digest generation...")

        # Import digest components
        try:
            from ..file_gate import FileGate
            from ..summarizer import Summarizer
            from ..writer import DigestWriter

            gate = FileGate(self.config)
            status = gate.check_all_gates(today)
            logger.info("File gate status:\n%s", status.summary())

            if status.all_inputs_ready:
                logger.info("All inputs ready, generating digest...")

                # Run summarization in a thread to avoid blocking the event loop (LLM calls are synchronous)
                def _generate_sync():
                    with Summarizer(self.config) as summarizer:
                        return summarizer.generate(status, today)

                result = await __import__("asyncio").to_thread(_generate_sync)

                if result.success:
                    # Write to file
                    writer = DigestWriter(self.config)
                    writer.write(result, today)

                    # Post to Discord
                    embed = self.create_digest_embed(
                        f"📊 Daily Digest — {today.isoformat()}",
                        result.content,
                        result.metadata,
                    )

                    await self.post_digest(
                        f"**Daily Market Intelligence for {today.strftime('%A, %B %d, %Y')}**",
                        embed=embed,
                    )

                    self._last_digest_date = today
                    logger.info("Digest posted successfully!")
                else:
                    logger.warning(f"Digest generation failed: {result.error}")

                    # Fallback: use deterministic, DB-based report to ensure something useful posts
                    try:
                        from db_manager import DatabaseManager

                        from ..daily_report import build_report

                        logger.info("Attempting deterministic fallback digest from DB")
                        db = DatabaseManager()
                        fallback_msg = build_report(db, hours=24)

                        if fallback_msg:
                            writer = DigestWriter(self.config)
                            # Create a proper DigestResult for fallback
                            from ..summarizer import DigestResult

                            fr = DigestResult(content=fallback_msg, success=True, metadata={"fallback": True})

                            writer.write(fr, today)

                            embed = self.create_digest_embed(
                                f"📊 Daily Digest (Fallback) — {today.isoformat()}",
                                fallback_msg,
                                {"fallback": True},
                            )

                            await self.post_digest(
                                f"**Daily Market Intelligence (Fallback) for {today.strftime('%A, %B %d, %Y')}**",
                                embed=embed,
                            )

                            self._last_digest_date = today
                            logger.info("Fallback digest posted successfully")
                    except Exception:
                        logger.exception("Fallback digest generation/post failed")
            else:
                logger.info("Not all inputs ready yet")

        except Exception as e:
            logger.error(f"Digest check failed: {e}")
            self.healer.health.record_error(f"Digest check: {e}")

    @digest_check_loop.before_loop
    async def before_digest_check(self) -> None:
        """Wait for bot to be ready before checking digests."""
        await self.wait_until_ready()

    @tasks.loop(minutes=5)
    async def health_report_loop(self) -> None:
        """Periodically report health status."""
        await self._ready.wait()

        # Update component health
        self.healer.health.set_component_health(
            "discord",
            HealthState.HEALTHY if self.is_ready() else HealthState.UNHEALTHY,
        )

        self.healer.health.set_component_health(
            "latency",
            HealthState.HEALTHY if self.latency < 0.5 else HealthState.DEGRADED,
        )

        # Record heartbeat
        self.healer.health.record_heartbeat()

    @health_report_loop.before_loop
    async def before_health_report(self) -> None:
        """Wait for bot to be ready."""
        await self.wait_until_ready()

    # ══════════════════════════════════════════════════════════════════════════
    # COMMANDS
    # ══════════════════════════════════════════════════════════════════════════

    async def _register_commands(self) -> None:
        """Register slash commands."""

        @self.tree.command(name="digest", description="Generate and post today's digest")
        @app_commands.checks.has_permissions(manage_messages=True)
        async def digest_command(interaction: discord.Interaction):
            await interaction.response.defer()

            try:
                from ..file_gate import FileGate
                from ..summarizer import Summarizer

                gate = FileGate(self.config)
                status = gate.check_all_gates()

                if not status.all_inputs_ready:
                    await interaction.followup.send(
                        "⚠️ Not all inputs are ready. Missing:\n"
                        f"- Journal: {'✅' if status.journal_ready else '❌'}\n"
                        f"- Pre-market: {'✅' if status.premarket_ready else '❌'}\n"
                        f"- Weekly: {'✅' if status.weekly_ready else '❌'}"
                    )
                    return

                with Summarizer(self.config) as summarizer:
                    result = summarizer.generate(status)

                if result.success:
                    embed = self.create_digest_embed(
                        f"📊 Daily Digest — {date.today().isoformat()}",
                        result.content,
                        result.metadata,
                    )
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send(f"❌ Generation failed: {result.error}")

            except Exception as e:
                await interaction.followup.send(f"❌ Error: {e}")

        @self.tree.command(name="health", description="Show bot health status")
        async def health_command(interaction: discord.Interaction):
            status = self.healer.health

            state_emoji = {
                HealthState.HEALTHY: "🟢",
                HealthState.DEGRADED: "🟡",
                HealthState.UNHEALTHY: "🟠",
                HealthState.RECOVERING: "🔵",
                HealthState.CRITICAL: "🔴",
            }

            embed = discord.Embed(
                title=f"{state_emoji.get(status.state, '⚪')} Bot Health Status",
                color=discord.Color.green() if status.state == HealthState.HEALTHY else discord.Color.orange(),
            )

            embed.add_field(name="State", value=status.state.name, inline=True)
            embed.add_field(name="Uptime", value=status.uptime_str, inline=True)
            embed.add_field(name="Latency", value=f"{self.latency*1000:.0f}ms", inline=True)
            embed.add_field(name="Reconnects", value=str(status.reconnect_count), inline=True)
            embed.add_field(name="Total Errors", value=str(status.total_errors), inline=True)
            embed.add_field(name="Consec. Errors", value=str(status.consecutive_errors), inline=True)

            if status.components:
                components_str = "\n".join(f"{k}: {v.name}" for k, v in status.components.items())
                embed.add_field(name="Components", value=components_str, inline=False)

            await interaction.response.send_message(embed=embed)

        @self.tree.command(name="setup", description="Run server setup (creates channels/roles)")
        @app_commands.checks.has_permissions(administrator=True)
        async def setup_command(interaction: discord.Interaction):
            await interaction.response.defer()

            # Analyze first
            analysis = await self.guide.analyze_server(interaction.guild)

            if not analysis["needs_setup"]:
                await interaction.followup.send("✅ Server structure is already complete!")
                return

            # Apply blueprint
            report = await self.guide.apply_blueprint(interaction.guild)

            embed = discord.Embed(
                title="🏗️ Server Setup Complete",
                color=discord.Color.green(),
            )

            if report["roles_created"]:
                embed.add_field(
                    name="Roles Created",
                    value="\n".join(report["roles_created"]),
                    inline=True,
                )

            if report["categories_created"]:
                embed.add_field(
                    name="Categories Created",
                    value="\n".join(report["categories_created"]),
                    inline=True,
                )

            if report["channels_created"]:
                embed.add_field(
                    name="Channels Created",
                    value="\n".join(report["channels_created"]),
                    inline=True,
                )

            if report["errors"]:
                embed.add_field(
                    name="⚠️ Errors",
                    value="\n".join(report["errors"][:5]),
                    inline=False,
                )

            await self._cache_channels()
            await interaction.followup.send(embed=embed)

        @self.tree.command(name="invite", description="Generate a server invite")
        @app_commands.checks.has_permissions(create_instant_invite=True)
        async def invite_command(interaction: discord.Interaction):
            invite_url = await self.create_invite()

            if invite_url:
                await interaction.response.send_message(
                    f"🔗 **Server Invite**\n{invite_url}",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "❌ Failed to create invite",
                    ephemeral=True,
                )

        @self.tree.command(name="whoami", description="Show bot identity and purpose")
        async def whoami_command(interaction: discord.Interaction):
            embed = discord.Embed(
                title="🤖 Digest Bot Identity",
                description=BOT_IDENTITY,
                color=discord.Color.gold(),
            )
            await interaction.response.send_message(embed=embed)

        @self.tree.command(
            name="publish_changelog", description="Publish changelog into the resources channel and pin it (operators)"
        )
        @app_commands.checks.has_permissions(manage_messages=True)
        async def publish_changelog_cmd(interaction: discord.Interaction):
            await interaction.response.defer()
            try:
                import io
                from pathlib import Path

                changelog = Path(self.config.root_dir) / "docs" / "changelog" / "CHANGELOG.md"
                if not changelog.exists():
                    await interaction.followup.send("Changelog file not found.", ephemeral=True)
                    return

                content = changelog.read_text(encoding="utf-8")
                first_heading = None
                for line in content.splitlines():
                    if line.startswith("## "):
                        first_heading = line.strip("# ")
                        break

                ch = None
                if self.guide:
                    ch = self.guide.get_channel("📚-resources")

                if not ch and interaction.guild:
                    ch = discord.utils.get(interaction.guild.text_channels, name="📚-resources")

                if not ch:
                    await interaction.followup.send(
                        "Resources channel not found; run `/setup` or create `📚-resources`.", ephemeral=True
                    )
                    return

                file = discord.File(io.BytesIO(content.encode("utf-8")), filename="CHANGELOG.md")
                msg = await ch.send(
                    f"📣 **Changelog published**\n{first_heading or 'Full changelog attached.'}", file=file
                )
                try:
                    await msg.pin(reason="Published changelog via slash command")
                except Exception:
                    pass

                await interaction.followup.send(f"Changelog posted to {ch.mention} and pinned.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"Failed to publish changelog: {e}", ephemeral=True)

        @self.tree.command(
            name="pin_commands", description="Post and pin the public command guide into resources channel (operators)"
        )
        @app_commands.checks.has_permissions(manage_messages=True)
        async def pin_commands_cmd(interaction: discord.Interaction):
            await interaction.response.defer()
            try:
                ch = None
                if self.guide:
                    ch = self.guide.get_channel("📚-resources")

                if not ch and interaction.guild:
                    ch = discord.utils.get(interaction.guild.text_channels, name="📚-resources")

                if not ch:
                    await interaction.followup.send("Resources channel not found.", ephemeral=True)
                    return

                commands_text = (
                    "**Bot commands**\n"
                    "- `/digest` — Generate and post today's digest.\n"
                    "- `/health` — Show bot health.\n"
                    "- `/publish_changelog` — Publish changelog to resources (operators).\n"
                    "- `/pin_commands` — Post and pin this guide (operators).\n"
                )

                msg = await ch.send(commands_text)
                try:
                    await msg.pin(reason="Pinned command guide via slash command")
                except Exception:
                    pass

                await interaction.followup.send(f"Command guide posted to {ch.mention} and pinned.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"Failed to post command guide: {e}", ephemeral=True)

    # ══════════════════════════════════════════════════════════════════════════
    # RUNNING
    # ══════════════════════════════════════════════════════════════════════════

    async def start_with_healing(self) -> None:
        """
        Start the bot with self-healing reconnection.

        Automatically handles disconnections and errors.
        """
        token = self.config.discord.bot_token

        if not token:
            raise ValueError("Discord bot token not configured. " "Set DISCORD_BOT_TOKEN environment variable.")

        async def connect():
            await self.start(token)

        while not self.healer.is_shutting_down():
            try:
                await connect()
            except discord.LoginFailure:
                logger.error("Invalid Discord token!")
                raise
            except Exception as e:
                logger.error(f"Bot crashed: {e}")
                self.healer.health.record_error(str(e))

                if not self.healer.is_shutting_down():
                    await self.healer.wait_before_reconnect()

    def run_forever(self) -> None:
        """Run the bot with event loop management."""
        try:
            asyncio.run(self.start_with_healing())
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
            self.healer.request_shutdown()


# ══════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════


def run_discord_bot(config: Optional[Config] = None) -> None:
    """
    Run the Discord bot.

    Args:
        config: Configuration (uses global if None)
    """
    if not DISCORD_AVAILABLE:
        print("ERROR: discord.py is not installed.")
        print("Install with: pip install discord.py")
        sys.exit(1)

    config = config or get_config()

    if not config.discord.bot_token:
        print("ERROR: DISCORD_BOT_TOKEN environment variable not set.")
        sys.exit(1)

    bot = DigestDiscordBot(config)
    bot.run_forever()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run_discord_bot()
