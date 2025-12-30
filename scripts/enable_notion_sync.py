#!/usr/bin/env python3
"""Enable Notion publishing and sync all unsynced documents."""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.expanduser("~/syndicate"))

db_path = os.path.expanduser("~/syndicate/data/syndicate.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Enable Notion publishing
cursor.execute(
    "INSERT OR REPLACE INTO system_config (key, value, description, updated_at) VALUES (?, ?, ?, datetime('now'))",
    ("notion_publishing_enabled", "true", "Enable Notion publishing"),
)
conn.commit()
print("✓ Enabled Notion publishing")

# Check it's now enabled
cursor.execute("SELECT value FROM system_config WHERE key = 'notion_publishing_enabled'")
row = cursor.fetchone()
print(f"  Current value: {row[0] if row else 'NOT SET'}")

conn.close()

# Now trigger sync for existing documents
print("\n=== Syncing documents to Notion ===")
try:
    from pathlib import Path

    from scripts.notion_publisher import NotionPublisher

    pub = NotionPublisher()
    output_dir = Path(os.path.expanduser("~/syndicate/output"))
    reports_dir = output_dir / "reports"

    synced = 0
    failed = 0

    # Sync journals
    for f in output_dir.glob("Journal_*.md"):
        print(f"  Syncing: {f.name}")
        try:
            result = pub.sync_file(str(f), doc_type="journal")
            if result:
                synced += 1
                print("    ✓ Synced to Notion")
            else:
                print("    - Already synced or skipped")
        except Exception as e:
            failed += 1
            print(f"    ✗ Failed: {e}")

    # Sync premarket reports
    for f in reports_dir.glob("premarket/*.md"):
        print(f"  Syncing: {f.name}")
        try:
            result = pub.sync_file(str(f), doc_type="premarket")
            if result:
                synced += 1
                print("    ✓ Synced to Notion")
            else:
                print("    - Already synced or skipped")
        except Exception as e:
            failed += 1
            print(f"    ✗ Failed: {e}")

    print(f"\n=== Summary: {synced} synced, {failed} failed ===")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()
