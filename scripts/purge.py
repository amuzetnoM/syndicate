#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════════════
#  _________._____________.___ ____ ___  _________      .__         .__
# /   _____/|   \______   \   |    |   \/   _____/____  |  | ______ |  |__ _____
# \_____  \ |   ||       _/   |    |   /\_____  \__  \ |  | \____ \|  |  \__  \
# /        \|   ||    |   \   |    |  / /        \/ __ \|  |_|  |_> >   Y  \/ __ \_
# /_______  /|___||____|_  /___|______/ /_______  (____  /____/   __/|___|  (____  /
#         \/             \/                     \/     \/     |__|        \/     \/
#
# Syndicate - Precious Metals Intelligence System
# Copyright (c) 2025 SIRIUS Alpha
# All rights reserved.
# ══════════════════════════════════════════════════════════════════════════════
"""
Consolidated purge script (Notion, imgbb, output)

This script performs the following steps:
 - Clear output files (hard delete if requested)
 - Purge imgbb chart cache and local charts
 - Archive Notion pages in configured database (or optionally list only)

Defaults to a dry run. Use --execute --force to skip prompts and run destructive actions.
"""

import argparse
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load environment variables
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

OUTPUT_DIR = PROJECT_ROOT / "output"
ARCHIVE_DIR = OUTPUT_DIR / "archive" / datetime.now().strftime("%Y%m%d%H%M%S")
CACHE_FILE = OUTPUT_DIR / "chart_urls.json"
CHART_DIR = OUTPUT_DIR / "charts"


# Notion
try:
    from notion_client import Client

    NOTION_AVAILABLE = True
except Exception:
    NOTION_AVAILABLE = False


def list_output_files():
    files = []
    for p in OUTPUT_DIR.rglob("*"):
        if p.is_file():
            files.append(p)
    return files


def clear_outputs(dry_run=True, hard_delete=False):
    files = list_output_files()
    if not files:
        return {"count": 0, "files": []}

    if dry_run:
        return {"count": len(files), "files": [str(p) for p in files[:100]]}

    if hard_delete:
        deleted = 0
        failed = []
        for p in files:
            try:
                p.unlink()
                deleted += 1
            except Exception:
                try:
                    if p.is_dir():
                        shutil.rmtree(p)
                        deleted += 1
                except Exception as e2:
                    failed.append((str(p), str(e2)))
        if failed:
            print(f"Warning: Failed to delete {len(failed)} items")
        return {"deleted": deleted, "failed": len(failed)}

    # Move to archive (non-hard-delete destructive route)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    moved = 0
    failed = []
    for p in files:
        if ARCHIVE_DIR in p.parents:
            continue
        rel = p.relative_to(OUTPUT_DIR)
        dest = ARCHIVE_DIR / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            p.replace(dest)
            moved += 1
        except Exception:
            try:
                shutil.copy2(p, dest)
                p.unlink()
                moved += 1
            except Exception as e:
                failed.append((str(p), str(e)))
    if failed:
        print(f"Warning: Failed to archive {len(failed)} items")
    return {"moved": moved, "failed": len(failed), "archived_to": str(ARCHIVE_DIR)}


# Chart cache purging


def load_chart_cache():
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def attempt_remote_delete(entry: dict) -> bool:
    delete_url = entry.get("delete_url")
    if not delete_url:
        return False
    try:
        resp = requests.get(delete_url)
        return resp.status_code in (200, 204)
    except Exception:
        return False


def purge_imgbb(dry_run=True, execute=False):
    cache = load_chart_cache()
    charts = cache.get("charts", {}) if isinstance(cache, dict) else {}

    if dry_run:
        return {"count": len(charts), "sample": list(charts.items())[:20]}

    deleted_remote = 0
    for k, v in charts.items():
        if attempt_remote_delete(v):
            deleted_remote += 1

    if CACHE_FILE.exists():
        try:
            CACHE_FILE.unlink()
        except Exception as e:
            print(f"Warning: Failed to delete cache file: {e}")

    deleted_local = 0
    failed_local = 0
    if CHART_DIR.exists():
        for f in CHART_DIR.glob("*"):
            if f.is_file():
                try:
                    f.unlink()
                    deleted_local += 1
                except Exception:
                    failed_local += 1
    if failed_local:
        print(f"Warning: Failed to delete {failed_local} local chart files")
    return {"deleted_local": deleted_local, "failed_local": failed_local, "deleted_remote": deleted_remote}


# Notion purging


def list_notion_pages(api_key: str, database_id: str, patterns: list[str] = None):
    if not NOTION_AVAILABLE:
        raise ImportError("notion-client not installed")

    client = Client(auth=api_key)
    pages = []
    start_cursor = None

    # Prefer databases.query if available
    if hasattr(client, "databases") and hasattr(client.databases, "query"):
        while True:
            query = {"database_id": database_id, "page_size": 100}
            if start_cursor:
                query["start_cursor"] = start_cursor
            resp = client.databases.query(**query)
            for p in resp.get("results", []):
                title = "Untitled"
                props = p.get("properties", {})
                name_prop = props.get("Name") or props.get("title")
                if name_prop:
                    title = name_prop.get("title", [{}])[0].get("plain_text", "Untitled")
                pages.append({"id": p["id"], "title": title})
            start_cursor = resp.get("next_cursor")
            if not start_cursor:
                break
    else:
        while True:
            resp = client.search(page_size=100, start_cursor=start_cursor)
            for p in resp.get("results", []):
                parent = p.get("parent", {})
                if parent.get("database_id") == database_id:
                    title = "Untitled"
                    props = p.get("properties", {})
                    name_prop = props.get("Name") or props.get("title")
                    if name_prop:
                        title = name_prop.get("title", [{}])[0].get("plain_text", "Untitled")
                    pages.append({"id": p["id"], "title": title})
            start_cursor = resp.get("next_cursor")
            if not start_cursor:
                break
    # If we found pages, or the caller didn't provide patterns, return results
    if pages or not patterns:
        return pages

    # If no pages found and patterns provided, search by patterns to find pages with titles
    found = []
    for pat in patterns:
        start_cursor = None
        while True:
            resp = client.search(query=pat, page_size=100, start_cursor=start_cursor)
            for p in resp.get("results", []):
                if p.get("object") != "page":
                    continue
                title = "Untitled"
                props = p.get("properties", {})
                name_prop = props.get("Name") or props.get("title")
                if name_prop:
                    title = name_prop.get("title", [{}])[0].get("plain_text", "Untitled")
                found.append({"id": p["id"], "title": title})
            start_cursor = resp.get("next_cursor")
            if not start_cursor:
                break

    # Deduplicate by ID
    ids = set()
    deduped = []
    for p in found:
        if p["id"] not in ids:
            ids.add(p["id"])
            deduped.append(p)

    return deduped


def archive_notion_pages(api_key: str, page_ids: list):
    if not NOTION_AVAILABLE:
        raise ImportError("notion-client not installed")
    client = Client(auth=api_key)
    archived_count = 0
    failed = []
    for pid in page_ids:
        try:
            client.pages.update(page_id=pid, archived=True)
            archived_count += 1
        except Exception as e:
            failed.append({"id": pid, "error": str(e)})
            print(f"Failed to archive {pid}: {e}")
    return {"archived": archived_count, "failed": failed}


def purge_notion(dry_run=True, execute=False, patterns: list[str] = None):
    api_key = os.getenv("NOTION_API_KEY") or ""
    db_id = os.getenv("NOTION_DATABASE_ID") or ""

    if not api_key or not db_id:
        return {"error": "Notion API key or database not configured"}

    pages = list_notion_pages(api_key, db_id, patterns=patterns)

    if dry_run:
        return {"count": len(pages), "sample": pages[:50]}

    # Archive pages
    archived = archive_notion_pages(api_key, [p["id"] for p in pages])
    # support both old numeric return and new dict return
    if isinstance(archived, dict):
        return archived
    return {"archived": archived}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="purge.py", description="Consolidated purge: output, charts, Notion")
    parser.add_argument("--execute", action="store_true", help="Perform destructive actions")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done (default)")
    parser.add_argument("--force", action="store_true", help="Skip confirmations")
    parser.add_argument(
        "--notion-patterns", nargs="*", help="List of title-patterns to target for Notion deletion (space-separated)"
    )
    parser.add_argument("--hard-delete", action="store_true", help="Hard-delete local outputs instead of archiving")
    args = parser.parse_args()

    if not args.execute and not args.dry_run:
        args.dry_run = True

    print("\nRunning purge script (dry-run)" if args.dry_run else "\nRunning purge script (execute)")

    # 1) Clear outputs
    out_res = clear_outputs(dry_run=args.dry_run, hard_delete=args.hard_delete)
    if args.dry_run:
        print(f"[OUTPUT] Would remove {out_res.get('count')} files. Sample:\n  ")
        for f in out_res.get("files", [])[:20]:
            print(" ", f)
    else:
        print(f"[OUTPUT] Result: {out_res}")

    # 2) Purge imgbb chart cache
    img_res = purge_imgbb(dry_run=args.dry_run, execute=args.execute)
    if args.dry_run:
        print(f"[IMGBB] Found {img_res.get('count')} cached chart(s). Sample:\n  ")
        for k, v in img_res.get("sample", [])[:20]:
            print("   ", k, v.get("url", ""))
    else:
        print(f"[IMGBB] Result: {img_res}")

    # 3) Purge Notion pages
    notion_res = purge_notion(dry_run=args.dry_run, execute=args.execute, patterns=args.notion_patterns)
    if "error" in notion_res:
        print(f"[NOTION] Skipped: {notion_res['error']}")
    elif args.dry_run:
        print(f"[NOTION] Found {notion_res.get('count')} pages. Sample:\n  ")
        for p in notion_res.get("sample", [])[:20]:
            print("   ", p["title"], p["id"])
    else:
        print(f"[NOTION] Archived {notion_res.get('archived', 0)} pages")

    # If we executed and forced, do not prompt anymore. Otherwise, if about to execute and not forced, ask to confirm.
    if args.execute and not args.force:
        confirm = input("Execute destructive purge (Outputs/IMGBB/Notion)? [y/N]: ")
        if confirm.strip().lower() != "y":
            print("Aborted")
            raise SystemExit(0)

    print("\nPurge script complete")
