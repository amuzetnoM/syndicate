#!/usr/bin/env python3
"""Sync document frontmatter status into DB and optionally publish to Notion.

Usage:
  python scripts/sync_db_frontmatter.py [--apply] [--publish]

--apply   : write status changes to DB (dry-run by default)
--publish : attempt to publish files whose frontmatter status is 'published' (requires NOTION env)
"""
import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.frontmatter import parse_frontmatter
from db_manager import get_db
try:
    from syndicate.utils.env_loader import load_env
    load_env()
except Exception:
    pass


def find_markdown_files(root: Path):
    for p in root.glob("**/*.md"):
        yield p


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write status updates to DB")
    parser.add_argument("--publish", action="store_true", help="Attempt to publish files marked published")
    args = parser.parse_args()

    db = get_db()
    output_dir = PROJECT_ROOT / "output"

    updated = 0
    registered = 0
    to_publish = []

    for md in find_markdown_files(output_dir):
        try:
            content = md.read_text(encoding="utf-8")
        except Exception:
            continue

        meta, _ = parse_frontmatter(content)
        status = meta.get("status", "draft")
        doc_type = meta.get("type") or None

        normalized = str(md.resolve())
        row = db.get_document_status(normalized)

        if not row:
            # Register document
            if args.apply:
                db.register_document(normalized, doc_type or "notes", status=status, content_hash=db.get_file_hash(normalized))
            registered += 1
        else:
            if row.get("status") != status:
                if args.apply:
                    db.update_document_status(normalized, status)
                updated += 1

        if status == "published":
            to_publish.append(normalized)

    print(f"Scanned output: registered={registered}, status_changed={updated}, publishable={len(to_publish)}")

    if args.publish and to_publish:
        try:
            from scripts.notion_publisher import NotionPublisher
            pub = NotionPublisher()
        except Exception as e:
            print(f"Cannot import NotionPublisher: {e}")
            return

        published = 0
        failed = 0
        for path in to_publish:
            try:
                res = pub.sync_file(path, force=True)
                if res.get("skipped"):
                    print(f"Skipped publish {path}: {res.get('reason')}")
                    continue
                published += 1
                print(f"Published: {path} -> {res.get('page_id')}")
            except Exception as e:
                print(f"Failed publish {path}: {e}")
                failed += 1

        print(f"Publish summary: published={published}, failed={failed}")
    # end
    # Note: Publishing tasks are tracked/marked by external workflow; this script does not toggle those flags automatically. Consider adding db flagging here if desired.


if __name__ == "__main__":
    main()
