#!/usr/bin/env python3
"""Check system configs and attempt a manual Notion publish."""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.expanduser("~/syndicate"))

db_path = os.path.expanduser("~/syndicate/data/syndicate.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=== System Config ===")
cursor.execute("SELECT key, value FROM system_config WHERE key LIKE '%notion%' OR key LIKE '%publish%'")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

print("\n=== All System Config ===")
cursor.execute("SELECT key, value FROM system_config")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close()

# Try a test publish
print("\n=== Testing Notion API ===")
try:
    from scripts.notion_publisher import NotionPublisher

    pub = NotionPublisher()
    print(f"  API Key: {pub.config.api_key[:20]}...")
    print(f"  Database ID: {pub.config.database_id}")
    print("  Notion client initialized successfully!")
except Exception as e:
    print(f"  ERROR: {e}")
