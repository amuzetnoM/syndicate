#!/usr/bin/env python3
"""Post today's premarket and journal to admin reports channel via Bot REST API.

Usage: .venv/bin/python scripts/post_reports_to_admin.py

Requires environment:
- DISCORD_BOT_TOKEN (bot token)
- DISCORD_GUILD_ID (guild id)

The script finds today's premarket and journal files (by filename patterns) and posts a short summary to the admin reports channel (📥-reports).
"""

import os
import sys
import json
from datetime import date
from pathlib import Path

import requests
import re
import yaml

# Add project src to path for config
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from digest_bot.config import get_config


def find_file(directory: Path, prefix: str, target_date: date) -> Path | None:
    patterns = [f"{prefix}_{target_date.isoformat()}.md", f"{prefix}{target_date.isoformat()}.md", f"{target_date.isoformat()}_{prefix}.md"]
    for p in patterns:
        candidate = directory / p
        if candidate.exists():
            return candidate

    # Fallback: try glob searching for date
    for f in directory.glob(f"*{target_date.isoformat()}*.md"):
        if prefix in f.name.lower():
            return f

    return None


def snippet_of(path: Path, length: int = 600) -> str:
    try:
        text = path.read_text(encoding="utf-8")
        # Strip YAML frontmatter if present
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) == 3:
                text = parts[2]

        clean = text.strip()
        return clean[:length] + ("..." if len(clean) > length else "")
    except Exception:
        return "(failed to read file)"


def parse_frontmatter(path: Path) -> tuple[dict, str]:
    """Return (frontmatter_dict, body_text) for a markdown file with YAML frontmatter.

    If no frontmatter present, returns ({}, full_text).
    """
    try:
        text = path.read_text(encoding="utf-8")
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) == 3:
                fm_text = parts[1]
                body = parts[2].strip()
                try:
                    fm = yaml.safe_load(fm_text) or {}
                except Exception:
                    fm = {}
                return fm, body
        return {}, text
    except Exception:
        return {}, "(failed to read file)"


def get_reports_channel_id(token: str, guild_id: int) -> int | None:
    url = f"https://discord.com/api/v10/guilds/{guild_id}/channels"
    headers = {"Authorization": f"Bot {token}"}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    channels = r.json()

    for ch in channels:
        if ch.get("name") == "📥-reports":
            return int(ch["id"])
    return None


def get_channel_id_by_name(token: str, guild_id: int, name: str) -> int | None:
    url = f"https://discord.com/api/v10/guilds/{guild_id}/channels"
    headers = {"Authorization": f"Bot {token}"}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    channels = r.json()

    for ch in channels:
        if ch.get("name") == name:
            return int(ch["id"])
    return None


def create_text_channel_if_missing(token: str, guild_id: int, name: str, topic: str | None = None, publisher_role_ids: list[int] | None = None) -> int | None:
    """Create a text channel in the guild if it doesn't exist and return its id.

    Returns channel id or None on failure.
    """
    existing = get_channel_id_by_name(token, guild_id, name)
    if existing:
        return existing

    url = f"https://discord.com/api/v10/guilds/{guild_id}/channels"
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    # Build permission_overwrites: deny @everyone send_messages, allow publisher roles to send messages
    overwrites = []
    # Deny SEND_MESSAGES (0x00000800 = 2048) for @everyone (role id == guild id)
    overwrites.append({"id": str(guild_id), "type": 0, "deny": str(2048), "allow": "0"})
    if publisher_role_ids:
        for rid in publisher_role_ids:
            overwrites.append({"id": str(rid), "type": 0, "allow": str(2048), "deny": "0"})

    payload = {"name": name, "type": 0, "permission_overwrites": overwrites}
    if topic:
        payload["topic"] = topic

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        if r.status_code in (200, 201):
            ch = r.json()
            return int(ch.get("id"))
        else:
            print("Failed to create channel:", r.status_code, r.text)
            return None
    except Exception as e:
        print("Exception creating channel:", e)
        return None


def post_message(token: str, channel_id: int, content: str) -> bool:
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    payload = {"content": content}
    r = requests.post(url, headers=headers, json=payload, timeout=10)
    if r.status_code in (200, 201):
        return True
    else:
        print("Failed to post message:", r.status_code, r.text)
        return False


def post_with_embed_and_files(token: str, channel_id: int, content: str, embed: dict | None = None, file_paths: list[Path] | None = None) -> bool:
    """
    Post a message with an embed and optional file attachments using multipart payload.
    """
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {token}"}

    payload = {"content": content}
    if embed:
        payload["embeds"] = [embed]

    files = []
    files_payload = []
    if file_paths:
        for i, p in enumerate(file_paths):
            try:
                mime = "application/octet-stream"
                if p.suffix.lower() in (".png", ".jpg", ".jpeg"):
                    mime = "image/png"
                elif p.suffix.lower() in (".md", ".markdown"):
                    mime = "text/markdown"
                files_payload.append((f"files[{i}]", (p.name, open(p, "rb"), mime)))
            except Exception as e:
                print(f"Failed to open attachment {p}: {e}")

    try:
        data = {"payload_json": json.dumps(payload)}
        r = requests.post(url, headers=headers, data=data, files=files_payload, timeout=20)
        if r.status_code in (200, 201):
            return True
        else:
            print("Failed multipart post:", r.status_code, r.text)
            return False
    finally:
        # close any opened file objects
        for _n, fp in files_payload:
            try:
                fp[1].close()
            except Exception:
                pass


def main():
    cfg = get_config()
    token = os.environ.get("DISCORD_BOT_TOKEN") or cfg.discord.bot_token
    guild_id = os.environ.get("DISCORD_GUILD_ID") or cfg.discord.guild_id

    if not token:
        print("DISCORD_BOT_TOKEN not set; aborting")
        sys.exit(1)
    if not guild_id:
        print("DISCORD_GUILD_ID not set; aborting")
        sys.exit(1)

    gid = int(guild_id)
    channel_id = get_reports_channel_id(token, gid)
    if not channel_id:
        print("Could not find 📥-reports channel in guild")
        sys.exit(1)

    today = date.today()

    # Try configured premarket dir first, then fall back to the top-level reports dir
    pre_file = find_file(cfg.paths.premarket_dir, "premarket", today)
    if not pre_file:
        pre_file = find_file(cfg.paths.reports_dir, "premarket", today)
    journal_file = find_file(cfg.paths.journals_dir, "Journal", today)

    content_lines = [f"**Automated report delivery — {today.isoformat()}**"]

    if pre_file:
        content_lines.append("\n__Pre-Market Plan:__")
        content_lines.append(snippet_of(pre_file, 700))
        # Add Notion URL if available
        try:
            from db_manager import DatabaseManager

            db = DatabaseManager()
            with db._get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT notion_url FROM notion_sync WHERE file_path = ? ORDER BY synced_at DESC LIMIT 1",
                    (str(pre_file),),
                )
                row = cur.fetchone()
                if row and row[0]:
                    content_lines.append(f"Notion: {row[0]}")
        except Exception:
            pass
        content_lines.append(f"(Full file: `{pre_file}`)")
        # Also post to public premarket channel with embed + attachments
        try:
            public_ch = get_channel_id_by_name(token, int(guild_id), "📈-premarket-plans")
            if public_ch:
                # Parse frontmatter and build enriched embed
                fm, body = parse_frontmatter(pre_file)
                desc = snippet_of(pre_file, 600)
                generated_ts = fm.get("generated") or fm.get("date") or "N/A"

                # Attempt to detect bias from frontmatter tags or body
                bias = "N/A"
                tags = fm.get("tags")
                if tags:
                    # tags may be a list or comma-separated string
                    if isinstance(tags, list):
                        for t in tags:
                            if str(t).lower() in ("bullish", "bearish"):
                                bias = str(t)
                                break
                    else:
                        for t in str(tags).split(","):
                            if t.strip().lower() in ("bullish", "bearish"):
                                bias = t.strip()
                                break
                if bias == "N/A":
                    m = re.search(r"Overall Bias:.*\*\*(\w+)\*\*", body, re.IGNORECASE)
                    if m:
                        bias = m.group(1).upper()

                embed = {
                    "title": f"Pre-Market Plan — {today.isoformat()}",
                    "description": desc,
                    "color": 0xFFD700,
                    "fields": [],
                }

                # Try to attach top chart and the markdown
                charts_dir = Path(cfg.paths.project_root) / "output" / "charts"
                chart_candidate = None
                if charts_dir.exists():
                    for cand in ("GOLD.png", "SPX.png", "DXY.png"):
                        p = charts_dir / cand
                        if p.exists():
                            chart_candidate = p
                            break

                attachments = []
                if chart_candidate:
                    attachments.append(chart_candidate)
                # Attach the full markdown
                attachments.append(Path(pre_file))

                # Add Notion link field if present in DB
                notion_url = None
                try:
                    from db_manager import DatabaseManager

                    db = DatabaseManager()
                    with db._get_connection() as conn:
                        cur = conn.cursor()
                        cur.execute(
                            "SELECT notion_url FROM notion_sync WHERE file_path = ? ORDER BY synced_at DESC LIMIT 1",
                            (str(pre_file),),
                        )
                        row = cur.fetchone()
                        if row and row[0]:
                            notion_url = row[0]
                except Exception:
                    notion_url = None

                # Add embed fields
                embed_fields = []
                embed_fields.append({"name": "Bias", "value": bias, "inline": True})
                embed_fields.append({"name": "Generated", "value": str(generated_ts), "inline": True})
                embed_fields.append({"name": "Notion", "value": notion_url or "N/A", "inline": False})
                embed["fields"] = embed_fields

                # Set thumbnail to the chart attachment if present
                if chart_candidate:
                    embed["thumbnail"] = {"url": f"attachment://{chart_candidate.name}"}

                post_with_embed_and_files(token, public_ch, f"Pre-Market Plan — {today.isoformat()}", embed=embed, file_paths=attachments)
        except Exception:
            pass
    else:
        content_lines.append("\n__Pre-Market Plan:__ (not found)")

    if journal_file:
        content_lines.append("\n__Journal:__")
        content_lines.append(snippet_of(journal_file, 700))
        # Add Notion URL if available for journal as well
        try:
            from db_manager import DatabaseManager

            db = DatabaseManager()
            with db._get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT notion_url FROM notion_sync WHERE file_path = ? ORDER BY synced_at DESC LIMIT 1",
                    (str(journal_file),),
                )
                row = cur.fetchone()
                if row and row[0]:
                    content_lines.append(f"Notion: {row[0]}")
        except Exception:
            pass
        content_lines.append(f"(Full file: `{journal_file}`)")
        # Post to public journal channel (create if missing)
        try:
            journal_name = "📔-trading-journal"
            public_journal_ch = get_channel_id_by_name(token, int(guild_id), journal_name)
            if not public_journal_ch:
                # Attempt to create channel using known spec
                public_journal_ch = create_text_channel_if_missing(token, int(guild_id), journal_name, "📝 Daily trading journal entries and reflections.")

            if public_journal_ch:
                # Parse frontmatter for journal and enrich embed
                fm_j, body_j = parse_frontmatter(journal_file)
                desc_j = snippet_of(journal_file, 800)
                generated_j = fm_j.get("generated") or fm_j.get("date") or "N/A"

                bias_j = "N/A"
                tags_j = fm_j.get("tags")
                if tags_j:
                    if isinstance(tags_j, list):
                        for t in tags_j:
                            if str(t).lower() in ("bullish", "bearish"):
                                bias_j = str(t)
                                break
                    else:
                        for t in str(tags_j).split(","):
                            if t.strip().lower() in ("bullish", "bearish"):
                                bias_j = t.strip()
                                break
                if bias_j == "N/A":
                    m = re.search(r"Overall Bias:.*\*\*(\w+)\*\*", body_j, re.IGNORECASE)
                    if m:
                        bias_j = m.group(1).upper()

                embed_j = {
                    "title": f"Trading Journal — {today.isoformat()}",
                    "description": desc_j,
                    "color": 0x4B9CD3,
                    "fields": [
                        {"name": "Bias", "value": bias_j, "inline": True},
                        {"name": "Generated", "value": str(generated_j), "inline": True},
                    ],
                }

                # Attach journal markdown and optionally a chart (chart first so thumbnail works)
                attachments_j = [Path(journal_file)]
                charts_dir = Path(cfg.paths.project_root) / "output" / "charts"
                chart_for_j = None
                if charts_dir.exists():
                    for cand in ("SPX.png", "GOLD.png", "DXY.png"):
                        p = charts_dir / cand
                        if p.exists():
                            chart_for_j = p
                            attachments_j.insert(0, p)
                            break

                if chart_for_j:
                    embed_j["thumbnail"] = {"url": f"attachment://{chart_for_j.name}"}

                # Add Notion link for journal if present
                try:
                    from db_manager import DatabaseManager

                    db = DatabaseManager()
                    with db._get_connection() as conn:
                        cur = conn.cursor()
                        cur.execute(
                            "SELECT notion_url FROM notion_sync WHERE file_path = ? ORDER BY synced_at DESC LIMIT 1",
                            (str(journal_file),),
                        )
                        row = cur.fetchone()
                        if row and row[0]:
                            embed_j["fields"].append({"name": "Notion", "value": row[0], "inline": False})
                except Exception:
                    pass

                post_with_embed_and_files(token, public_journal_ch, f"Trading Journal — {today.isoformat()}", embed=embed_j, file_paths=attachments_j)
        except Exception:
            pass
    else:
        content_lines.append("\n__Journal:__ (not found)")

    content = "\n\n".join(content_lines)

    ok = post_message(token, channel_id, content)
    if ok:
        print("Posted reports to admin channel")
    else:
        print("Failed to post reports")


if __name__ == "__main__":
    main()
