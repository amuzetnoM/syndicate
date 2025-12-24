#!/usr/bin/env python3
"""Archive Notion pages referenced in the digest cleanup backup.

Reads `output/notion_digest_cleanup_backup.json` and archives each page
using the Notion API (marks pages as `archived=True`). Logs results.

This script requires `NOTION_API_KEY` to be set in the environment.
"""
import os
import json
import logging
from pathlib import Path

try:
    from notion_client import Client
except Exception:
    Client = None

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("notion_cleanup")

BACKUP = Path("output") / "notion_digest_cleanup_backup.json"


def page_id_from_url(url: str) -> str | None:
    if not url:
        return None
    # Notion URLs often end with the page id (with or without hyphens)
    parts = url.rstrip("/").split("-")
    last = parts[-1]
    # if URL contains hyphenated uuid like 2d3743b4-... return that
    if "-" in last and len(last) >= 32:
        return last
    # Else try to strip trailing path parts
    import re
    m = re.search(r"([0-9a-fA-F]{32}|[0-9a-fA-F\-]{36})$", url)
    if m:
        return m.group(1)
    return None


def main():
    if Client is None:
        LOG.error("notion-client not installed. Please pip install notion-client in the venv.")
        return 2

    api_key = os.getenv("NOTION_API_KEY")
    if not api_key:
        LOG.error("NOTION_API_KEY not set in environment; cannot archive pages")
        return 2

    if not BACKUP.exists():
        LOG.error("Backup file not found: %s", BACKUP)
        return 1

    with open(BACKUP, "r") as f:
        rows = json.load(f)

    client = Client(auth=api_key)
    results = []
    for r in rows:
        page_id = r.get("notion_page_id") or r.get("notion_page") or page_id_from_url(r.get("notion_url"))
        if not page_id:
            LOG.warning("No page id for row: %s", r.get("file_path"))
            results.append({"file": r.get("file_path"), "status": "no_page_id"})
            continue
        try:
            LOG.info("Archiving Notion page %s for file %s", page_id, r.get("file_path"))
            client.pages.update(page_id=page_id, archived=True)
            results.append({"file": r.get("file_path"), "page_id": page_id, "status": "archived"})
        except Exception as e:
            LOG.exception("Failed to archive page %s: %s", page_id, e)
            results.append({"file": r.get("file_path"), "page_id": page_id, "status": "error", "error": str(e)})

    # Write results log
    out = Path("output") / "notion_digest_cleanup_archive_results.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    LOG.info("Archive run complete; results written to %s", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
