#!/usr/bin/env python3
"""List all actions in the DB with verbose output for debugging."""
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db_manager import get_db


def main():
    db = get_db()
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM action_insights ORDER BY created_at DESC")
        rows = cursor.fetchall()
        if not rows:
            print("No actions found in DB")
            return 0
        for r in rows:
            row = dict(r)
            print(f"ID: {row.get('action_id')} | status={row.get('status')} | priority={row.get('priority')} | created_at={row.get('created_at')}")
            # print metadata if exists
            if row.get('metadata'):
                try:
                    print("  metadata:", row.get('metadata'))
                except Exception:
                    print("  metadata: (unprintable)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
