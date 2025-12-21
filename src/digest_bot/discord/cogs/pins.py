from __future__ import annotations

import logging
from discord.ext import commands
import discord

LOG = logging.getLogger("digest_bot.discord.pins")

class PinsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pin_latest")
    @commands.has_role("operators")
    async def cmd_pin_latest(self, ctx, channel_name: str = None, keep: int = 5):
        """Pin the latest message in a channel (default: current). Keeps only `keep` pinned messages."""
        if channel_name:
            ch = discord.utils.get(ctx.guild.text_channels, name=channel_name)
            if not ch:
                await ctx.send(f"Channel `{channel_name}` not found.")
                return
        else:
            ch = ctx.channel

        # Find latest non-pinned message (or latest message overall)
        last = None
        async for msg in ch.history(limit=50):
            if msg.pinned:
                continue
            last = msg
            break

        if not last:
            await ctx.send("No message found to pin (channel may only contain pinned messages).")
            return

        try:
            await last.pin(reason=f"Pinned by {ctx.author}")
            # Enforce keep limit
            pinned = await ch.pins()
            if len(pinned) > keep:
                # Unpin oldest first
                to_unpin = sorted(pinned, key=lambda m: m.created_at)[: len(pinned) - keep]
                for m in to_unpin:
                    try:
                        await m.unpin(reason="Auto-unpin to enforce keep limit")
                    except Exception:
                        LOG.exception("Failed to unpin message")
            await ctx.send(f"Pinned message in {ch.mention}. Now {len(await ch.pins())} pinned messages.")
        except discord.Forbidden:
            await ctx.send("Bot lacks permission to pin messages in that channel.")
        except Exception as e:
            LOG.exception("Failed to pin message")
            await ctx.send(f"Failed to pin message: {e}")

    @commands.command(name="pin_daily_charts")
    @commands.has_role("operators")
    async def cmd_pin_daily_charts(self, ctx, channel_name: str = "📈-day-charts", keep: int = 5):
        """Scan a channel for recent messages with attachments/embeds and pin the most recent ones."""
        ch = discord.utils.get(ctx.guild.text_channels, name=channel_name)
        if not ch:
            await ctx.send(f"Channel `{channel_name}` not found.")
            return

        found = []
        async for msg in ch.history(limit=200):
            if msg.attachments or msg.embeds:
                found.append(msg)
            if len(found) >= keep:
                break

        if not found:
            await ctx.send(f"No chart messages found in {ch.mention}.")
            return

        # Pin the found messages (most recent first)
        pinned_count = 0
        for m in found:
            try:
                if not m.pinned:
                    await m.pin(reason="Auto-pin daily chart")
                    pinned_count += 1
            except Exception:
                LOG.exception("Failed to pin chart message")

        # enforce keep limit
        pinned = await ch.pins()
        if len(pinned) > keep:
            to_unpin = sorted(pinned, key=lambda m: m.created_at)[: len(pinned) - keep]
            for m in to_unpin:
                try:
                    await m.unpin(reason="Auto-unpin older charts to enforce keep limit")
                except Exception:
                    LOG.exception("Failed to unpin old chart")

        await ctx.send(f"Pinned {pinned_count} chart messages in {ch.mention}. Total pins now {len(await ch.pins())}.")


def setup(bot):
    return PinsCog(bot)
