#!/usr/bin/env python3
"""Daily LLM operations report and Discord sender.

Generates a concise report about the LLM queue, sanitizer corrections and flagged
items over a recent window (default: last 24 hours) and optionally posts it to
Discord via `scripts/notifier.send_discord` using `DISCORD_WEBHOOK_URL` or an
explicit webhook passed via --webhook.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
import argparse
from typing import Optional

from . import __version__ as DIGEST_BOT_VERSION
from db_manager import DatabaseManager
from scripts.notifier import send_discord

LOG = logging.getLogger("digest_bot.daily_report")

DEFAULT_HOURS = 24


import glob
import os


def _extract_premarket_summary() -> tuple[str, str, str]:
    """Find the latest premarket file and extract Overall Bias, Rationale and Notion URL if available.

    Returns (bias, rationale, notion_url) — empty strings if not found.
    """
    import sqlite3

    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "output", "reports")

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
    now = datetime.utcnow()
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
    lines.append(f"**Gold Standard — LLM Daily Report** (last {hours}h)")
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


def send(hours: int = DEFAULT_HOURS, webhook: Optional[str] = None, dry_run: bool = False) -> bool:
    db = DatabaseManager()
    msg = build_report(db, hours=hours)
    if dry_run:
        print(msg)
        return True

    # Attempt to send via Discord webhook
    ok = send_discord(msg, webhook_url=webhook)
    if not ok:
        LOG.warning("Failed to send daily report to Discord; falling back to stdout")
        print(msg)
    return ok


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
