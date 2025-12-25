#!/usr/bin/env python3
"""Remove notion_sync rows that are placeholders/tests (not real Notion pages).

Backs up the rows to output/notion_test_rows_backup.json then deletes them and
resets document_lifecycle for those paths.
"""
import sqlite3
import json
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "syndicate.db"
OUT = Path(__file__).resolve().parent.parent / "output" / "notion_test_rows_backup.json"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Find rows where notion_url contains 'notion.test' or notion_page_id in ('pid') or notion_url is empty
cur.execute("SELECT * FROM notion_sync WHERE notion_url LIKE '%notion.test%' OR notion_page_id = 'pid' OR notion_page_id IS NULL OR notion_page_id = ''")
rows = [dict(r) for r in cur.fetchall()]
print('found', len(rows), 'rows')
if rows:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, 'w') as f:
        json.dump(rows, f, indent=2)
    for r in rows:
        fp = r['file_path']
        cur.execute('DELETE FROM notion_sync WHERE file_path = ?', (fp,))
        cur.execute('UPDATE document_lifecycle SET status = "draft", notion_page_id = NULL WHERE file_path = ?', (fp,))
    conn.commit()
    print('deleted rows and reset document_lifecycle; backup at', OUT)
else:
    print('no placeholder rows found')

conn.close()
