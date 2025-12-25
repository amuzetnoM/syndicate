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
Quick Notion debug: list pages by patterns and optionally archive them.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

try:
    from notion_client import Client
except Exception as e:
    print("notion-client not installed:", e)
    raise SystemExit(1)

api_key = os.getenv("NOTION_API_KEY")
db_id = os.getenv("NOTION_DATABASE_ID")
if not api_key or not db_id:
    print("NOTION_API_KEY or NOTION_DATABASE_ID missing in environment")
    raise SystemExit(1)

client = Client(auth=api_key)

# Patterns to search
patterns = [
    "Journal",
    "PreMarket",
    "Monthly",
    "1Y",
    "3M",
    "Catalysts",
    "InstMatrix",
    "FILE_INDEX",
    "Journal_",
    "PreMarket_",
]

pages = []
for pat in patterns:
    start_cursor = None
    while True:
        resp = client.search(query=pat, page_size=100, start_cursor=start_cursor)
        for p in resp.get("results", []) or []:
            if p.get("object") != "page":
                continue
            title = "Untitled"
            props = p.get("properties", {})
            name_prop = props.get("Name") or props.get("title")
            if name_prop:
                title = name_prop.get("title", [{}])[0].get("plain_text", "Untitled")
            pages.append({"id": p["id"], "title": title, "parent": p.get("parent", {})})
        start_cursor = resp.get("next_cursor")
        if not start_cursor:
            break

# Deduplicate by id
ids = set()
dedup = []
for p in pages:
    if p["id"] not in ids:
        ids.add(p["id"])
        dedup.append(p)

print(f"Found {len(dedup)} pages:")
for p in dedup:
    print(f"- {p['title']} ({p['id']}) parent: {p['parent']}")

confirm = input("Archive these pages (set archived=True)? [y/N]: ")
if confirm.strip().lower() == "y":
    archived = 0
    for p in dedup:
        try:
            client.pages.update(page_id=p["id"], archived=True)
            archived += 1
        except Exception as e:
            print(f"Failed to archive {p['id']}: {e}")
    print(f"Archived {archived} pages")
else:
    print("Aborted")
