#!/usr/bin/env python3
"""Reset stuck tasks and restart services."""

import os
import sqlite3
import subprocess

db_path = os.path.expanduser("~/syndicate/data/syndicate.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Reset stuck tasks
cursor.execute("UPDATE llm_tasks SET status='pending' WHERE status='in_progress'")
print(f"Reset {cursor.rowcount} stuck in_progress tasks")
conn.commit()

# Check current status
cursor.execute("SELECT status, COUNT(*) FROM llm_tasks GROUP BY status")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close()

# Restart sentinel to pick up changes
print("\nRestarting syndicate-sentinel...")
subprocess.run(["sudo", "systemctl", "restart", "syndicate-sentinel.service"])
print("Done!")
