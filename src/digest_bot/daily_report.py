#!/usr/bin/env python3
"""Daily LLM operations report and Discord sender.

Generates a concise report about the LLM queue, sanitizer corrections and flagged
items over a recent window (default: last 24 hours) and optionally posts it to
Discord via `scripts/notifier.send_discord` using `DISCORD_WEBHOOK_URL` or an
explicit webhook passed via --webhook.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import logging
import argparse
from typing import Optional

from . import __version__ as DIGEST_BOT_VERSION
from db_manager import DatabaseManager
from scripts.notifier import send_discord
from .discord import templates as discord_templates

LOG = logging.getLogger("digest_bot.daily_report")

DEFAULT_HOURS = 24


import glob
import os


def _extract_premarket_summary() -> tuple[str, str, str]:
    """Find the latest premarket file and extract Overall Bias, Rationale and Notion URL if available.

    Returns (bias, rationale, notion_url) — empty strings if not found.
    """
    import sqlite3

    # Allow tests to override the project base dir via GOLD_STANDARD__BASE
    base_dir = os.getenv("GOLD_STANDARD__BASE") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    reports_dir = os.path.join(base_dir, "output", "reports")

    # Find the newest premarket file
    candidates = glob.glob(os.path.join(reports_dir, "premarket_*.md"))
    if not candidates:
        # also check premarket subdir
        candidates = glob.glob(os.path.join(reports_dir, "premarket", "*premarket*2025-*.md"))
    if not candidates:
        return "", "", ""

    latest = sorted(candidates)[-1]

    bias = ""
    rationale = ""
    try:
        with open(latest, "r", encoding="utf-8") as f:
            text = f.read()
        # Simple parsing
        m_bias = None
        m_rat = None
        for line in text.splitlines():
            l = line.strip()
            if l.startswith("*   **Overall Bias:**") or l.startswith("* **Overall Bias:**"):
                m_bias = l
            if l.startswith("*   **Rationale:**") or l.startswith("* **Rationale:**"):
                m_rat = l
            if m_bias and m_rat:
                break
        if m_bias:
            # extract after colon
            bias = m_bias.split(":", 1)[1].strip()
        if m_rat:
            rationale = m_rat.split(":", 1)[1].strip()
    except Exception:
        bias = ""
        rationale = ""

    notion_url = ""
    try:
        db = DatabaseManager()
        with db._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT notion_url FROM notion_sync WHERE file_path = ? ORDER BY synced_at DESC LIMIT 1", (latest,))
            row = cur.fetchone()
            if row and row[0]:
                notion_url = row[0]
    except Exception:
        notion_url = ""

    return bias, rationale, notion_url


def build_report(db: DatabaseManager, hours: int = DEFAULT_HOURS) -> str:
    """Build a plain-text report summarizing LLM queue and sanitizer activity.

    Returns a short markdown-friendly string suitable for Discord message body.
    """
    # Use timezone-aware UTC now to avoid deprecation warnings
    from datetime import timezone

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=hours)
    since_sql = since.strftime("%Y-%m-%d %H:%M:%S")

    queue_length = db.get_llm_queue_length()

    # Capture premarket summary if available
    bias, rationale, notion_url = _extract_premarket_summary()

    with db._get_connection() as conn:
        cursor = conn.cursor()

        # Sanitizer corrections in window
        cursor.execute(
            "SELECT SUM(corrections) as total FROM llm_sanitizer_audit WHERE created_at >= ?",
            (since_sql,),
        )
        row = cursor.fetchone()
        corrections_total = int(row["total"] or 0)

        # Recent sanitizer records (limit)
        cursor.execute(
            "SELECT id, task_id, corrections, notes, created_at FROM llm_sanitizer_audit WHERE created_at >= ? ORDER BY created_at DESC LIMIT 10",
            (since_sql,),
        )
        recent_audits = cursor.fetchall()

        # Flagged tasks in window
        cursor.execute(
            "SELECT id, document_path, status, started_at, completed_at FROM llm_tasks WHERE status = 'flagged' AND completed_at >= ? ORDER BY completed_at DESC LIMIT 20",
            (since_sql,),
        )
        flagged_tasks = cursor.fetchall()

        # Errors in window
        cursor.execute(
            "SELECT id, document_path, error, attempts, completed_at FROM llm_tasks WHERE error IS NOT NULL AND completed_at >= ? ORDER BY completed_at DESC LIMIT 20",
            (since_sql,),
        )
        errors = cursor.fetchall()

        # Completed tasks count
        cursor.execute(
            "SELECT COUNT(1) as cnt FROM llm_tasks WHERE status = 'completed' AND completed_at >= ?",
            (since_sql,),
        )
        completed_cnt = cursor.fetchone()["cnt"]

    # Build message
    lines = []
    lines.append(f"**Syndicate — LLM Daily Report** (last {hours}h)")
    lines.append("")

    if bias:
        lines.append(f"**Pre-Market Summary:** **{bias}** — {rationale}")
        if notion_url:
            lines.append(f"Notion: {notion_url}")
        lines.append("")

    lines.append(f"- **Queue length**: {queue_length}")
    lines.append(f"- **Completed (last {hours}h)**: {completed_cnt}")
    lines.append(f"- **Sanitizer corrections (last {hours}h)**: {corrections_total}")
    lines.append("")

    if recent_audits:
        lines.append("**Recent sanitizer audits (up to 10):**")
        for a in recent_audits:
            notes = a["notes"] or ""
            ts = a["created_at"]
            lines.append(f"- id={a['id']} task_id={a['task_id']} corrections={a['corrections']} @ {ts} notes={notes}")
        lines.append("")

    if flagged_tasks:
        lines.append(f"**Flagged tasks (last {hours}h, up to 20):**")
        for t in flagged_tasks:
            lines.append(f"- id={t['id']} path={t['document_path']} completed_at={t['completed_at']}")
        lines.append("")

    if errors:
        lines.append("**Recent errors:**")
        for e in errors:
            lines.append(f"- id={e['id']} path={e['document_path']} attempts={e['attempts']} err={e['error']}")
        lines.append("")

    lines.append("_Report generated by Digest Bot v" + str(DIGEST_BOT_VERSION) + "_")

    return "\n".join(lines)


def build_structured_report(db: DatabaseManager, hours: int = DEFAULT_HOURS) -> dict:
    """Build a structured report suitable for embedding in Discord.

    Returns a dict containing top-level metrics and short lists for details.
    """
    from datetime import timezone

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=hours)
    since_sql = since.strftime("%Y-%m-%d %H:%M:%S")

    queue_length = db.get_llm_queue_length()

    bias, rationale, notion_url = _extract_premarket_summary()

    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT SUM(corrections) as total FROM llm_sanitizer_audit WHERE created_at >= ?",
            (since_sql,),
        )
        corrections_total = int(cursor.fetchone()["total"] or 0)

        cursor.execute(
            "SELECT COUNT(1) as cnt FROM llm_tasks WHERE status = 'completed' AND completed_at >= ?",
            (since_sql,),
        )
        completed_cnt = int(cursor.fetchone()["cnt"] or 0)

        # Small samples for details
        cursor.execute(
            "SELECT id, task_id, corrections, notes, created_at FROM llm_sanitizer_audit WHERE created_at >= ? ORDER BY created_at DESC LIMIT 8",
            (since_sql,),
        )
        recent_audits = [dict(r) for r in cursor.fetchall()]

        cursor.execute(
            "SELECT id, document_path, status, started_at, completed_at FROM llm_tasks WHERE status = 'flagged' AND completed_at >= ? ORDER BY completed_at DESC LIMIT 8",
            (since_sql,),
        )
        flagged_tasks = [dict(r) for r in cursor.fetchall()]

        cursor.execute(
            "SELECT id, document_path, error, attempts, completed_at FROM llm_tasks WHERE error IS NOT NULL AND completed_at >= ? ORDER BY completed_at DESC LIMIT 8",
            (since_sql,),
        )
        errors = [dict(r) for r in cursor.fetchall()]

    return {
        "generated_at": now.isoformat(),
        "hours": hours,
        "queue_length": queue_length,
        "completed": completed_cnt,
        "corrections": corrections_total,
        "premarket": {"bias": bias, "rationale": rationale, "notion_url": notion_url},
        "recent_audits": recent_audits,
        "flagged": flagged_tasks,
        "errors": errors,
    }


def send(hours: int = DEFAULT_HOURS, webhook: Optional[str] = None, dry_run: bool = False) -> bool:
    db = DatabaseManager()
    structured = build_structured_report(db, hours=hours)
    embed = discord_templates.build_daily_embed(structured)

    if dry_run:
        # Print a simple markdown representation and return
        print(discord_templates.plain_daily_text(structured))
        return True

    # Determine webhook URL: prefer explicit `webhook` arg, otherwise environment
    webhook_url = webhook or os.getenv("DISCORD_REPORTS_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK_URL")

    # Compute a fingerprint for this payload to avoid duplicate sends
    try:
        import hashlib, json
        payload_key = json.dumps(embed, sort_keys=True, default=str)
        fingerprint = hashlib.sha256(payload_key.encode('utf-8')).hexdigest()
    except Exception:
        fingerprint = None

    db = DatabaseManager()
    if fingerprint and db.was_discord_recent(webhook_url or "default", fingerprint, minutes=30):
        LOG.info("Skipping duplicate daily report send (recent fingerprint match)")
        return True

    ok = send_discord(None, webhook_url=webhook_url, embed=embed)
    if ok and fingerprint:
        try:
            db.record_discord_send(webhook_url or "default", fingerprint, hashlib.sha256(payload_key.encode('utf-8')).hexdigest())
        except Exception:
            pass
    if not ok:
        LOG.warning("Failed to send daily report embed to Discord; falling back to plaintext")
        # Attempt plain-text fallback using existing webhook env
        plain = build_report(db, hours=hours)
        fallback_ok = send_discord(plain, webhook_url=os.getenv("DISCORD_WEBHOOK_URL"))
        if not fallback_ok:
            print(plain)
        return fallback_ok
    return True


def main(argv: Optional[list] = None):
    parser = argparse.ArgumentParser(description="Send daily LLM operations report to Discord")
    parser.add_argument("-w", "--webhook", help="Discord webhook URL (overrides DISCORD_WEBHOOK_URL env)")
    parser.add_argument("-n", "--hours", type=int, default=DEFAULT_HOURS, help="Lookback window in hours")
    parser.add_argument("--dry-run", action="store_true", help="Print the report to stdout instead of sending")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)
    ok = send(hours=args.hours, webhook=args.webhook, dry_run=args.dry_run)
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
