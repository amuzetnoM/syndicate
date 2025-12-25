#!/usr/bin/env python3
"""Post system health summary to Discord.

Usage: python scripts/post_system_health.py

Environment:
  DISCORD_BOT_TOKEN, DISCORD_GUILD_ID
  SYSTEM_HEALTH_CHANNEL (optional) - channel name to post to (default: 📡-system-health)
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project src
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import sqlite3
from db_manager import DatabaseManager
from scripts.local_llm import LocalLLM

from scripts.post_reports_to_admin import get_channel_id_by_name, create_text_channel_if_missing, post_with_embed_and_files

SERVICE_NAMES = [
    "syndicate-premarket-watcher.service",
    "syndicate-offloaded-executor.service",
    "syndicate-run-once.service",
    "syndicate-model-cleanup.timer",
]

DEFAULT_CHANNEL = os.environ.get("SYSTEM_HEALTH_CHANNEL", "📡-system-health")


def run_cmd(cmd: list[str]) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def get_service_status(name: str) -> dict:
    # Use systemctl show for stable parsing
    rc, out, err = run_cmd(["systemctl", "show", "-p", "ActiveState", "-p", "SubState", "-p", "ExecMainStartTimestamp", name])
    if rc != 0:
        return {"name": name, "active": "unknown", "sub": "unknown", "since": None, "raw_error": err}

    data = { }
    for line in out.splitlines():
        if not line.strip():
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k] = v

    active = data.get("ActiveState", "unknown")
    sub = data.get("SubState", "unknown")
    since = data.get("ExecMainStartTimestamp")
    return {"name": name, "active": active, "sub": sub, "since": since}


def gather_db_stats(db: DatabaseManager) -> dict:
    with db._get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) as pending FROM llm_tasks WHERE status = 'pending'")
        pending = int(cur.fetchone()[0])

        cur.execute("SELECT COUNT(1) as started FROM llm_tasks WHERE status = 'started'")
        started = int(cur.fetchone()[0])

        cur.execute("SELECT COUNT(1) as failed_24 FROM task_execution_log WHERE success = 0 AND executed_at >= datetime('now', '-1 days')")
        failed_24 = int(cur.fetchone()[0])

        cur.execute("SELECT COUNT(1) as failures_total FROM task_execution_log WHERE success = 0")
        failed_total = int(cur.fetchone()[0])

    return {"pending": pending, "started": started, "failed_24": failed_24, "failed_total": failed_total}


def gather_model_stats(llm: LocalLLM, db: DatabaseManager) -> dict:
    models = llm.find_models()
    count = len(models)
    total_gb = sum([m.get("size_gb", 0.0) for m in models])
    # get unused candidates
    try:
        unused = db.get_unused_models(days_threshold=30, keep_list=os.environ.get("KEEP_LOCAL_MODELS", "").split(","), min_keep=1)
    except Exception:
        unused = []
    return {"count": count, "total_gb": total_gb, "unused_count": len(unused)}


def build_embed(service_statuses: list[dict], db_stats: dict, model_stats: dict) -> dict:
    from datetime import timezone
    now = datetime.now(timezone.utc).isoformat() + "Z"
    from datetime import timezone
    now = datetime.now(timezone.utc)
    embed = {
        "title": f"System Health — {now.date().isoformat()}",
        "description": f"Automated system health summary for {platform.node()}",
        "color": 0x00AAFF,
        "fields": [],
    }

    # Services field - list briefly, mark red if any not active
    svc_lines = []
    unhealthy = False
    for s in service_statuses:
        status = s.get("active") or "unknown"
        since = s.get("since") or "-"
        line = f"**{s['name']}**: {status} (since: {since})"
        svc_lines.append(line)
        if status != "active":
            unhealthy = True

    embed["fields"].append({"name": "Services", "value": "\n".join(svc_lines), "inline": False})

    embed["fields"].append({"name": "LLM Queue", "value": f"Pending: {db_stats['pending']}  •  Started: {db_stats['started']}\nFailed (24h): {db_stats['failed_24']}  •  Failures Total: {db_stats['failed_total']}", "inline": True})

    embed["fields"].append({"name": "Models", "value": f"Count: {model_stats['count']}  •  Size: {model_stats['total_gb']:.2f}GB\nUnused (30d): {model_stats['unused_count']}", "inline": True})

    if unhealthy or db_stats['failed_24'] > 0:
        embed["color"] = 0xFF4500
        embed["fields"].append({"name": "Action", "value": "Issues detected — check service statuses and task failures. Consider running `sudo systemctl status <service>` or inspect `task_execution_log` in DB.", "inline": False})
    else:
        embed["fields"].append({"name": "Status", "value": "All systems nominal.", "inline": False})

    embed["footer"] = {"text": f"Generated: {now}"}

    return embed


def main():
    token = os.environ.get("DISCORD_BOT_TOKEN")
    guild = os.environ.get("DISCORD_GUILD_ID")
    if not token or not guild:
        print("DISCORD_BOT_TOKEN or DISCORD_GUILD_ID not set; aborting")
        sys.exit(1)

    db = DatabaseManager()
    llm = LocalLLM()

    service_statuses = [get_service_status(s) for s in SERVICE_NAMES]
    db_stats = gather_db_stats(db)
    model_stats = gather_model_stats(llm, db)

    embed = build_embed(service_statuses, db_stats, model_stats)

    # Post to system channel (create if missing)
    channel_name = os.environ.get("SYSTEM_HEALTH_CHANNEL", DEFAULT_CHANNEL)
    ch = get_channel_id_by_name(token, int(guild), channel_name)
    if not ch:
        ch = create_text_channel_if_missing(token, int(guild), channel_name, "Automated system health reports and alerts.")

    if ch:
        post_with_embed_and_files(token, ch, "System Health Report", embed=embed, file_paths=None)
        print("Posted system health report to channel id", ch)
    else:
        print("Failed to locate or create system health channel; aborting")


if __name__ == "__main__":
    main()
