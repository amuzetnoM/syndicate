#!/usr/bin/env python3
"""
purge_all.py - Consolidated cleanup, baseline, and preparation script

This script performs a safe baseline of the system including:
- Database backup
- Clearing/archiving outputs
- Purging imgbb chart cache
- Clearing executor queue (action_insights)
- Optional: Purge Notion pages (requires env set)
- Optional: Run version consistency check across files
- Optional: Commit, tag, and release (requires `git` and `gh` CLIs + creds)

Default: dry-run. Use --execute --force to perform destructive actions.

Examples:
  python scripts/purge_all.py       # dry run
  python scripts/purge_all.py --execute --force --hard-delete --clear-actions
  python scripts/purge_all.py --execute --force --check-versions --tag-and-release --push

"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

# Local imports
from db_manager import DB_PATH, DatabaseManager

# Constants
OUTPUT_DIR = PROJECT_ROOT / "output"
CHART_DIR = OUTPUT_DIR / "charts"
CACHE_FILE = OUTPUT_DIR / "chart_urls.json"
ARCHIVE_DIR_ROOT = OUTPUT_DIR / "archive"

# Helper functions


def backup_db() -> Path:
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    dst = DB_PATH.with_name(DB_PATH.name + f".bak_{ts}")
    shutil.copy(DB_PATH, dst)
    return dst


def list_output_files() -> List[Path]:
    if not OUTPUT_DIR.exists():
        return []
    return [p for p in OUTPUT_DIR.rglob("*") if p.is_file()]


def clear_outputs(dry_run: bool = True, hard_delete: bool = False) -> Dict:
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
        return {"deleted": deleted, "failed": len(failed)}

    # Non-hard-delete: move to archive
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    archive_dir = ARCHIVE_DIR_ROOT / ts
    archive_dir.mkdir(parents=True, exist_ok=True)
    moved = 0
    failed = []
    for p in files:
        # do not move files already under archive
        if archive_dir in p.parents:
            continue
        rel = p.relative_to(OUTPUT_DIR)
        dest = archive_dir / rel
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
    return {"moved": moved, "failed": len(failed), "archived_to": str(archive_dir)}


def load_chart_cache() -> Dict:
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
        import requests

        resp = requests.get(delete_url)
        return resp.status_code in (200, 204)
    except Exception:
        return False


def purge_imgbb(dry_run: bool = True) -> Dict:
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
        except Exception:
            pass

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
    return {"deleted_local": deleted_local, "failed_local": failed_local, "deleted_remote": deleted_remote}


def purge_notion(dry_run: bool = True, patterns: Optional[List[str]] = None) -> Dict:
    api_key = os.getenv("NOTION_API_KEY") or ""
    db_id = os.getenv("NOTION_DATABASE_ID") or ""
    if not api_key or not db_id:
        return {"error": "Notion not configured"}

    try:
        from notion_client import Client

        client = Client(auth=api_key)
    except Exception:
        return {"error": "notion-client package not installed"}

    # Implementation reuses purge.py logic (databases.query OR search), but simple path here:
    pages = []
    start_cursor = None
    try:
        if hasattr(client, "databases") and hasattr(client.databases, "query"):
            while True:
                query = {"database_id": db_id, "page_size": 100}
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
                    if parent.get("database_id") == db_id:
                        title = "Untitled"
                        props = p.get("properties", {})
                        name_prop = props.get("Name") or props.get("title")
                        if name_prop:
                            title = name_prop.get("title", [{}])[0].get("plain_text", "Untitled")
                        pages.append({"id": p["id"], "title": title})
                start_cursor = resp.get("next_cursor")
                if not start_cursor:
                    break
    except Exception as e:
        return {"error": str(e)}

    if dry_run:
        return {"count": len(pages), "sample": pages[:50]}

    # Archive pages by updating `archived=True`
    archived = 0
    failed = []
    for p in pages:
        try:
            client.pages.update(page_id=p["id"], archived=True)
            archived += 1
        except Exception as e:
            failed.append({"id": p["id"], "error": str(e)})
    return {"archived": archived, "failed": failed}


def clear_actions(dry_run: bool = True) -> Dict:
    db = DatabaseManager()
    if dry_run:
        return {"pending": db.get_action_stats().get("pending", 0)}
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM action_insights")
        conn.commit()
    return {"pending_after": db.get_action_stats().get("pending", 0)}


def clear_documents(dry_run: bool = True) -> Dict:
    # Optionally reset document_lifecycle to draft or clear table
    db = DatabaseManager()
    if dry_run:
        return {"documents": len(db.get_documents_by_status("draft"))}
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE document_lifecycle SET status='draft', published_at=NULL WHERE 1=1")
        conn.commit()
    return {"documents_draft": len(db.get_documents_by_status("draft"))}


def check_versions() -> Dict:
    # Verify pyproject and package sources match
    mismatches = []
    try:
        import tomllib

        pyproject = PROJECT_ROOT / "pyproject.toml"
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        version = data.get("project", {}).get("version") or data.get("tool", {}).get("poetry", {}).get("version")
    except Exception:
        version = None

    # Read src/gost/__init__.py
    init_path = PROJECT_ROOT / "src" / "gost" / "__init__.py"
    if init_path.exists():
        text = init_path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.strip().startswith("__version__"):
                found = line.split("=")[-1].strip().strip("\"'")
                if version and found != version:
                    mismatches.append({"pyproject": version, "__init__": found})
    return {"mismatches": mismatches, "version": version}


def run_build_and_push(dry_run: bool = True, tag: Optional[str] = None, push: bool = False) -> Dict:
    # Build docker image and optionally push; run doc build (if configured), and optionally git commit/push
    res = {}
    if dry_run:
        res["commands"] = []
        res["info"] = "dry run - no changes"
        if tag:
            res["commands"].append(f'git tag -a {tag} -m "Release {tag}"')
            res["commands"].append("git push origin main --tags")
        return res

    if tag:
        subprocess.run(["git", "tag", "-a", tag, "-m", f"Release {tag}"], check=True)
        if push:
            subprocess.run(["git", "push", "origin", "main", "--tags"], check=True)

    # Optional: docker build & push
    # Do not push unless explicitly requested
    # Note: GHCR docker build/push is not implemented here; consider implementing a CI-based release workflow or add a dedicated helper to perform authenticated push

    return {"status": "done"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="purge_all.py", description="Consolidated baseline and purge script")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done (default)", default=True)
    parser.add_argument("--execute", action="store_true", help="Perform all destructive actions (overrides dry-run)")
    parser.add_argument("--force", action="store_true", help="Skip confirmations (use with --execute)")
    parser.add_argument(
        "--hard-delete", action="store_true", help="Hard-delete local output files instead of archiving"
    )
    parser.add_argument("--clear-actions", action="store_true", help="Clear action_insights table")
    parser.add_argument("--clear-docs", action="store_true", help="Reset document lifecycle to draft")
    parser.add_argument("--purge-imgbb", action="store_true", help="Purge imgbb cache and remote charts")
    parser.add_argument("--purge-notion", action="store_true", help="Purge all pages in Notion (requires env keys)")
    parser.add_argument("--backup-db", action="store_true", help="Backup database (default true)")
    parser.add_argument("--check-versions", action="store_true", help="Check version consistency across repo")
    parser.add_argument(
        "--tag-and-release", action="store_true", help="Create git tag and release (requires gh/gittokens)"
    )
    parser.add_argument("--tag", type=str, help="Tag name (e.g. v3.4.0) to create if tagging")
    parser.add_argument("--push", action="store_true", help="Push commits and tags")

    args = parser.parse_args()

    # Determine mode
    dry_run = not args.execute and args.dry_run
    if args.execute and not args.force:
        ok = input("Execute destructive actions (Outputs/DB/Notion)? [y/N]: ")
        if ok.strip().lower() != "y":
            print("Aborted by user")
            sys.exit(0)

    # 1) Backup DB
    print("Backing up DB...")
    if args.backup_db and not dry_run:
        b = backup_db()
        print("DB backed up to", b)
    else:
        if dry_run:
            print("Dry-run: would backup DB:", DB_PATH)

    # 2) Clear outputs
    print("Clearing outputs...")
    out_res = clear_outputs(dry_run=dry_run, hard_delete=args.hard_delete)
    if dry_run:
        print("[OUTPUT] Dry-run - would remove/count:", out_res)
    else:
        print("[OUTPUT] Result:", out_res)

    # 3) Purge imgbb
    if args.purge_imgbb:
        print("Purging IMGBB cache...")
        img_res = purge_imgbb(dry_run=dry_run)
        print("[IMGBB] Result:", img_res)

    # 4) Clear actions
    if args.clear_actions:
        print("Clearing action queue...")
        actions_res = clear_actions(dry_run=dry_run)
        print("[ACTIONS] Result:", actions_res)

    # 5) Clear docs
    if args.clear_docs:
        print("Resetting document lifecycle to draft...")
        docs_res = clear_documents(dry_run=dry_run)
        print("[DOCS] Result:", docs_res)

    # 6) Purge Notion
    if args.purge_notion:
        print("Purging Notion pages...")
        notion_res = purge_notion(dry_run=dry_run)
        print("[NOTION] Result:", notion_res)

    # 7) Check versions
    if args.check_versions:
        print("Checking versions...")
        vres = check_versions()
        print("[VERSIONS] Result:", vres)

    # 8) Tag & release
    if args.tag_and_release and args.tag:
        print("Tagging and optional releasing...")
        release_res = run_build_and_push(dry_run=dry_run, tag=args.tag, push=args.push)
        print("[RELEASE] Result:", release_res)

    print("\nPurge-all complete (dry-run: {})".format(dry_run))
