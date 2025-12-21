from __future__ import annotations

import io
import logging
from discord.ext import commands
import discord
from pathlib import Path

LOG = logging.getLogger("digest_bot.discord.resources")

CHANGELOG_PATH = Path(__file__).resolve().parents[2] / "docs" / "changelog" / "CHANGELOG.md"


class ResourcesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="publish_changelog")
    @commands.has_role("operators")
    async def cmd_publish_changelog(self, ctx, keep: int = 5):
        """Publish the repository changelog to the resources channel and pin it."""
        # Find channel
        ch = None
        if self.bot.guide:
            ch = self.bot.guide.get_channel("📚-resources")

        if not ch and ctx.guild:
            ch = discord.utils.get(ctx.guild.text_channels, name="📚-resources")

        if not ch:
            await ctx.send("Resources channel `📚-resources` not found. Run setup or create the channel.")
            return

        if not CHANGELOG_PATH.exists():
            await ctx.send("Changelog file not found in repo.")
            return

        try:
            content = CHANGELOG_PATH.read_text(encoding="utf-8")
            # Create a short summary (first heading block)
            first_heading = None
            for line in content.splitlines():
                if line.startswith("## "):
                    first_heading = line.strip("# ")
                    break

            file_bytes = io.BytesIO(content.encode("utf-8"))
            file = discord.File(file_bytes, filename="CHANGELOG.md")

            summary = f"📣 **Changelog published**\n{first_heading or 'Full changelog attached.'}"

            msg = await ch.send(summary, file=file)

            # Pin and enforce keep limit
            try:
                await msg.pin(reason=f"Published changelog by {ctx.author}")
                pinned = await ch.pins()
                if len(pinned) > keep:
                    to_unpin = sorted(pinned, key=lambda m: m.created_at)[: len(pinned) - keep]
                    for m in to_unpin:
                        try:
                            await m.unpin(reason="Auto-unpin to enforce keep limit")
                        except Exception:
                            LOG.exception("Failed to unpin message")
            except discord.Forbidden:
                await ctx.send("Bot lacks permission to pin messages in resources channel.")

            await ctx.send(f"Changelog posted to {ch.mention} and pinned.")
        except Exception as e:
            LOG.exception("Failed to publish changelog")
            await ctx.send(f"Failed to publish changelog: {e}")

    @commands.command(name="commands")
    async def cmd_commands(self, ctx, dm: bool = True):
        """List user-facing commands. Use `commands False` to post in-channel."""
        commands_text = (
            "**Bot commands**\n"
            "- `/digest` — Generate and post today's digest (operators or via permission).\n"
            "- `/health` — Show bot health status.\n"
            "- `!commands` — Show this list (DM by default).\n"
            "- `!pin_latest` — Pin the latest message in a channel (operators).\n"
            "- `!pin_daily_charts` — Pin recent chart messages in `📈-day-charts` (operators).\n"
        )

        if dm:
            try:
                await ctx.author.send(commands_text)
                if ctx.channel.type != discord.ChannelType.private:
                    await ctx.send("I've DM'd you the command list.")
            except discord.Forbidden:
                await ctx.send(commands_text)
        else:
            await ctx.send(commands_text)

    @commands.command(name="pin_commands")
    @commands.has_role("operators")
    async def cmd_pin_commands(self, ctx, keep: int = 3):
        """Post and pin the command guide to the resources channel."""
        ch = None
        if self.bot.guide:
            ch = self.bot.guide.get_channel("📚-resources")

        if not ch and ctx.guild:
            ch = discord.utils.get(ctx.guild.text_channels, name="📚-resources")

        if not ch:
            await ctx.send("Resources channel `📚-resources` not found.")
            return

        commands_text = (
            "**Bot commands**\n"
            "- `/digest` — Generate and post today's digest. (Operators)\n"
            "- `/health` — Show bot health.\n"
            "- `!commands` — DM or show a list of user-facing commands.\n"
            "- `!pin_latest` — Pin the latest message in a channel (operators).\n"
            "- `!pin_daily_charts` — Pin recent chart messages (operators).\n"
        )

        try:
            msg = await ch.send(commands_text)
            try:
                await msg.pin(reason=f"Pinned command guide by {ctx.author}")
                pinned = await ch.pins()
                if len(pinned) > keep:
                    to_unpin = sorted(pinned, key=lambda m: m.created_at)[: len(pinned) - keep]
                    for m in to_unpin:
                        try:
                            await m.unpin(reason="Auto-unpin to enforce keep limit")
                        except Exception:
                            LOG.exception("Failed to unpin message")
            except discord.Forbidden:
                await ctx.send("Bot lacks permission to pin messages in resources channel.")

            await ctx.send(f"Command guide posted to {ch.mention} and pinned.")
        except Exception as e:
            LOG.exception("Failed to post command guide")
            await ctx.send(f"Failed to post command guide: {e}")


def setup(bot):
    return ResourcesCog(bot)
