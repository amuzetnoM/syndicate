#!/usr/bin/env python3
"""Check LLM tasks and Notion sync status."""

import os
import sqlite3

db_path = os.path.expanduser("~/syndicate/data/syndicate.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=== LLM Tasks (Last 20) ===")
cursor.execute("SELECT id, status, document_path, created_at, last_attempt_at FROM llm_tasks ORDER BY id DESC LIMIT 20")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} | {row[2]} | created: {row[3]} | last: {row[4]}")

print("\n=== Notion Sync (Last 20) ===")
cursor.execute("SELECT id, file_path, notion_page_id, notion_url, synced_at FROM notion_sync ORDER BY id DESC LIMIT 20")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} | page_id: {row[2]} | synced: {row[4]}")

print("\n=== Stuck Tasks (in_progress) ===")
cursor.execute("SELECT id, document_path, status, last_attempt_at FROM llm_tasks WHERE status='in_progress'")
stuck = cursor.fetchall()
if stuck:
    for row in stuck:
        print(f"  STUCK: {row[0]} | {row[1]} | since: {row[3]}")
else:
    print("  None")

print("\n=== Document Lifecycle (Last 10) ===")
cursor.execute(
    "SELECT file_path, doc_type, status, published_at, notion_page_id FROM document_lifecycle ORDER BY id DESC LIMIT 10"
)
for row in cursor.fetchall():
    print(f"  {row[0]} | {row[1]} | status: {row[2]} | published: {row[3]}")

conn.close()
