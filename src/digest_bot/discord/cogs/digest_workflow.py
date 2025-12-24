from __future__ import annotations

import logging
import os
try:
    import discord
    from discord.ext import commands
    from discord import ButtonStyle
    from discord.ui import View
except Exception:
    # Provide lightweight fallbacks for environments without discord.py to allow test collection
    discord = None

    class ButtonStyle:
        green = "green"
        grey = "grey"
        blurple = "blurple"

    class View:
        def __init__(self, *args, **kwargs):
            pass

    class _DummyUI:
        @staticmethod
        def button(label=None, style=None):
            def decorator(fn):
                return fn

            return decorator

    # A minimal 'commands' stub with required decorators and Cog base class
    class _DummyCommands:
        class Cog:
            pass

        @staticmethod
        def command(name=None):
            def decorator(fn):
                return fn

            return decorator

        @staticmethod
        def has_role(role_name):
            def decorator(fn):
                return fn

            return decorator

    commands = _DummyCommands()

    # Provide a small ui namespace compatible with usage: discord.ui.button
    class _DummyDiscord:
        ui = _DummyUI()

    discord = _DummyDiscord()

LOG = logging.getLogger("digest_bot.discord.digest_workflow")

class ApproveView(View):
    def __init__(self, task_id: int, author_id: int):
        super().__init__(timeout=None)
        self.task_id = task_id
        self.author_id = author_id

    @discord.ui.button(label="Approve", style=ButtonStyle.green)
    async def approve(self, button, interaction):
        # Only operators may approve; ensure role check
        if "operators" not in [r.name for r in interaction.user.roles]:
            await interaction.response.send_message("You are not authorized to approve.", ephemeral=True)
            return
        from db_manager import get_db
        db = get_db()

        # Enforce sanitizer checks: ensure no corrections recorded for this task
        with db._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT SUM(corrections) as total FROM llm_sanitizer_audit WHERE task_id = ?", (self.task_id,))
            row = cur.fetchone()
            corrections = int(row["total"] or 0)
        if corrections > 0:
            await interaction.response.send_message(
                f"Task {self.task_id} has {corrections} sanitizer corrections and cannot be approved. Please review or re-run.",
                ephemeral=True,
            )
            db.save_bot_audit(str(interaction.user), "approve_failed", f"task={self.task_id} corrections={corrections}")
            return

        # Mark approved and audit
        ok = db.approve_llm_task(self.task_id, str(interaction.user))
        if ok:
            await interaction.response.send_message(f"Task {self.task_id} approved and marked completed by {interaction.user}")
        else:
            await interaction.response.send_message(f"Failed to approve task {self.task_id}", ephemeral=True)

    @discord.ui.button(label="Flag", style=ButtonStyle.grey)
    async def flag(self, button, interaction):
        if "operators" not in [r.name for r in interaction.user.roles]:
            await interaction.response.send_message("You are not authorized to flag.", ephemeral=True)
            return
        from db_manager import get_db
        db = get_db()
        db.save_bot_audit(str(interaction.user), "flag", f"task={self.task_id}")
        await interaction.response.send_message(f"Task {self.task_id} flagged for review by {interaction.user}")

    @discord.ui.button(label="Re-run", style=ButtonStyle.blurple)
    async def rerun(self, button, interaction):
        if "operators" not in [r.name for r in interaction.user.roles]:
            await interaction.response.send_message("You are not authorized to rerun.", ephemeral=True)
            return
        from db_manager import get_db
        db = get_db()
        # Copy task and insert new pending task
        with db._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT document_path, prompt FROM llm_tasks WHERE id = ?", (self.task_id,))
            row = cur.fetchone()
            if not row:
                await interaction.response.send_message("Task not found", ephemeral=True)
                return
            cur.execute("INSERT INTO llm_tasks (document_path, prompt, provider_hint, status) VALUES (?, ?, ?, 'pending')", (row['document_path'], row['prompt'], None))
        db.save_bot_audit(str(interaction.user), "rerun", f"task={self.task_id}")
        await interaction.response.send_message(f"Task {self.task_id} re-enqueued by {interaction.user}")


class DigestWorkflowCog(commands.Cog):
    """Cog that exposes operator-facing workflows around digests."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="digest_full")
    @commands.has_role("operators")
    async def cmd_digest_full(self, ctx, period: int = 24):
        """Generate a full digest and post to channel with approval UI (operators only)."""
        from ..daily_report import build_structured_report
        from ..discord import templates as discord_templates
        from db_manager import DatabaseManager
        db = DatabaseManager()
        # Build structured report and render embed
        structured = build_structured_report(db, hours=period)
        embed_dict = discord_templates.build_daily_embed(structured)

        # Convert to discord.Embed if library is available
        embed_obj = None
        try:
            if hasattr(discord, 'Embed'):
                embed_obj = discord.Embed.from_dict(embed_dict)
        except Exception:
            embed_obj = None

        # Create a synthetic task id for UI actions if not tied to an existing task
        task_id = 0
        view = ApproveView(task_id, ctx.author.id)
        if embed_obj is not None:
            await ctx.send(embed=embed_obj, view=view)
        else:
            # Fallback to plaintext
            await ctx.send(discord_templates.plain_daily_text(structured), view=view)

    @commands.command(name="preview_digest")
    @commands.has_role("operators")
    async def cmd_preview_digest(self, ctx, period: int = 24, send: bool = False):
        """Preview the digest in-channel or print to console; operators only.

        Usage: `!preview_digest 24` (shows embed locally)
        """
        from db_manager import DatabaseManager
        db = DatabaseManager()
        structured = build_structured_report(db, hours=period)
        embed_dict = discord_templates.build_daily_embed(structured)

        try:
            embed_obj = discord.Embed.from_dict(embed_dict) if hasattr(discord, 'Embed') else None
        except Exception:
            embed_obj = None

        if send:
            # Send to channel but respect dedupe
            try:
                import hashlib, json
                payload_key = json.dumps(embed_dict, sort_keys=True, default=str)
                fingerprint = hashlib.sha256(payload_key.encode('utf-8')).hexdigest()
            except Exception:
                fingerprint = None
            db = DatabaseManager()
            channel_key = str(ctx.channel.id) if ctx and hasattr(ctx.channel, 'id') else 'channel'
            if fingerprint and db.was_discord_recent(channel_key, fingerprint, minutes=5):
                await ctx.send("Skipping send: recent duplicate fingerprint", ephemeral=True)
                return
            if embed_obj is not None:
                await ctx.send(embed=embed_obj)
            else:
                await ctx.send(discord_templates.plain_daily_text(structured))
            if fingerprint:
                db.record_discord_send(channel_key, fingerprint, hashlib.sha256(payload_key.encode('utf-8')).hexdigest())
            return

        # Local preview in channel
        if embed_obj is not None:
            await ctx.send(embed=embed_obj)
        else:
            await ctx.send(discord_templates.plain_daily_text(structured))

    @commands.command(name="recent_sends")
    @commands.has_role("operators")
    async def cmd_recent_sends(self, ctx, limit: int = 10):
        """List recent Discord sends recorded by the system (operators only)."""
        from db_manager import DatabaseManager
        db = DatabaseManager()
        with db._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, channel, fingerprint, sent_at FROM discord_messages ORDER BY sent_at DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
        if not rows:
            await ctx.send("No recent sends recorded.")
            return
        lines = [f"id={r['id']} channel={r['channel']} sent_at={r['sent_at']} fp={r['fingerprint'][:12]}..." for r in rows]
        await ctx.send("\n".join(lines))

    @commands.command(name="clear_fingerprint")
    @commands.has_role("operators")
    async def cmd_clear_fingerprint(self, ctx, fingerprint: str):
        """Remove stored sends for a fingerprint so a message may be re-sent."""
        from db_manager import DatabaseManager
        db = DatabaseManager()
        with db._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM discord_messages WHERE fingerprint = ?", (fingerprint,))
            deleted = cur.rowcount
        await ctx.send(f"Cleared {deleted} records for fingerprint {fingerprint[:12]}...")

    @commands.command(name="resend_daily")
    @commands.has_role("operators")
    async def cmd_resend_daily(self, ctx, hours: int = 24, webhook: str = None):
        """Rebuild and resend the daily report (operators only)."""
        from ..daily_report import build_structured_report, DEFAULT_HOURS
        from db_manager import DatabaseManager
        db = DatabaseManager()
        structured = build_structured_report(db, hours=hours or DEFAULT_HOURS)
        embed = discord_templates.build_daily_embed(structured)
        # Dedup check
        try:
            import hashlib, json
            payload_key = json.dumps(embed, sort_keys=True, default=str)
            fingerprint = hashlib.sha256(payload_key.encode('utf-8')).hexdigest()
        except Exception:
            fingerprint = None

        channel_key = webhook or (str(ctx.channel.id) if hasattr(ctx.channel, 'id') else 'channel')
        db = DatabaseManager()
        if fingerprint and db.was_discord_recent(channel_key, fingerprint, minutes=1):
            await ctx.send("Recent duplicate found; skipped resend.")
            return

        # Send via webhook if provided, otherwise to current channel
        from scripts.notifier import send_discord
        ok = False
        if webhook:
            ok = send_discord(None, webhook_url=webhook, embed=embed)
        else:
            try:
                embed_obj = discord.Embed.from_dict(embed) if hasattr(discord, 'Embed') else None
                if embed_obj:
                    await ctx.send(embed=embed_obj)
                    ok = True
                else:
                    await ctx.send(discord_templates.plain_daily_text(structured))
                    ok = True
            except Exception:
                ok = False

        if ok and fingerprint:
            db.record_discord_send(channel_key, fingerprint, hashlib.sha256(payload_key.encode('utf-8')).hexdigest())
        await ctx.send("Resend completed" if ok else "Resend failed")


def setup(bot):
    return DigestWorkflowCog(bot)
