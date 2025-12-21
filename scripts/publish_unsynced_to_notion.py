#!/usr/bin/env python3
"""Publish any unsynced report files to Notion using NotionPublisher.

This script looks for files under `output/reports` (and subfolders) and
publishes any files that are not present in the `notion_sync` table.

It requires `NOTION_API_KEY` and `NOTION_DATABASE_ID` present in env or `.env`.
"""
import os
import sys
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("publish_unsynced_to_notion")

ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT
REPORTS_DIR = REPO_ROOT / "output" / "reports"

try:
    from scripts.notion_publisher import NotionPublisher, NotionConfig
except Exception as e:
    LOG.error("NotionPublisher not available: %s", e)
    LOG.error("Install notion-client and ensure NOTION_API_KEY/NOTION_DATABASE_ID are set in .env or environment")
    sys.exit(2)

try:
    from db_manager import get_db
except Exception as e:
    LOG.error("DB manager not available: %s", e)
    sys.exit(2)


def list_unsynced_reports() -> list[Path]:
    db = get_db()
    # Collect all report files
    files = [p for p in REPORTS_DIR.rglob("*.md")]

    # Query notion_sync table for existing file_paths
    with db._get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT file_path FROM notion_sync")
        rows = cur.fetchall()
        synced = {r[0] for r in rows}

    unsynced = [p for p in files if str(p) not in synced]
    return unsynced


def publish(paths: list[Path]):
    cfg = NotionConfig.from_env()
    pub = NotionPublisher(cfg)

    for p in paths:
        try:
            LOG.info("Publishing %s to Notion", p)
            pub.publish_file(str(p))
        except Exception as e:
            LOG.exception("Failed to publish %s: %s", p, e)


def main(argv=None):
    unsynced = list_unsynced_reports()
    if not unsynced:
        LOG.info("No unsynced reports found")
        return 0

    LOG.info("Found %s unsynced reports", len(unsynced))
    publish(unsynced)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())