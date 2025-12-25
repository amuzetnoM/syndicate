#!/usr/bin/env python3
"""Compute document metrics and post a summary to Discord reports channel.
Usage:
  python scripts/discord_report_metrics.py --dry-run
  python scripts/discord_report_metrics.py --send

Environment:
  DISCORD_REPORTS_WEBHOOK (optional, falls back to DISCORD_WEBHOOK_URL)
"""
import os
from pathlib import Path
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.notifier import send_discord
from scripts.notion_publisher import NotionPublisher, TYPE_PATTERNS
from db_manager import get_db


def classify_file(publisher: NotionPublisher, path: Path) -> str:
    return publisher.detect_type(path.name)


def gather_output_counts(output_dir: str = None) -> dict:
    output_dir = output_dir or str(PROJECT_ROOT / "output")
    out = Path(output_dir)
    pub = NotionPublisher(no_client_ok=True)
    counts = {}
    md_files = list(out.glob("**/*.md"))
    for f in md_files:
        ft = classify_file(pub, f)
        counts[ft] = counts.get(ft, 0) + 1
    # include digests folder count
    digests = list(out.glob("digests/*.md")) if (out / "digests").exists() else []
    counts["digests"] = len(digests)
    return counts


def gather_db_counts() -> dict:
    db = get_db()
    rows = db.get_all_synced_files()
    counts = {}
    for r in rows:
        dt = r.get("doc_type") or "unknown"
        counts[dt] = counts.get(dt, 0) + 1
    return counts


def build_message(output_counts: dict, db_counts: dict) -> dict:
    # Build a compact embed and plain text summary
    title = "Syndicate — Reports Summary"
    lines = []
    lines.append("Output directory counts:")
    for k, v in sorted(output_counts.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("Notion sync counts:")
    for k, v in sorted(db_counts.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"- {k}: {v}")

    content = "\n".join(lines)
    embed = {
        "title": title,
        "description": content[:4096],
        "color": 3447003,
    }
    return {"content": content, "embed": embed}


def main(dry_run: bool = True, send: bool = False):
    out_counts = gather_output_counts()
    db_counts = gather_db_counts()
    msg = build_message(out_counts, db_counts)

    if dry_run:
        print("--- Discord Reports Metrics (preview) ---")
        print(msg["content"]) 

    if send:
        webhook = os.getenv("DISCORD_REPORTS_WEBHOOK") or os.getenv("DISCORD_WEBHOOK_URL")
        ok = send_discord(None, webhook_url=webhook, embed=msg["embed"])
        if ok:
            print("Sent metrics to Discord reports webhook")
        else:
            print("Failed to send metrics to Discord webhook")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--send', action='store_true')
    args = parser.parse_args()
    main(dry_run=args.dry_run, send=args.send)
