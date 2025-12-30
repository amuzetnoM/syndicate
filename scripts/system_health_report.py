#!/usr/bin/env python3
"""
Syndicate System Health Report
Comprehensive diagnostic output for developers.
Like a hospital report - full overview, all metrics, straight and simple.
"""

import os
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

# Load .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ[key.strip()] = value.strip()


def run_cmd(cmd: str) -> str:
    """Run a shell command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"


def get_service_status(service: str) -> dict:
    """Get detailed status of a systemd service."""
    status = run_cmd(f"systemctl is-active {service}")
    enabled = run_cmd(f"systemctl is-enabled {service}")
    memory = run_cmd(f"systemctl show {service} --property=MemoryCurrent --value")
    pid = run_cmd(f"systemctl show {service} --property=MainPID --value")

    return {
        "status": status,
        "enabled": enabled,
        "memory_mb": int(memory) // 1024 // 1024 if memory.isdigit() else "N/A",
        "pid": pid if pid and pid != "0" else "N/A",
    }


def main():
    print("=" * 70)
    print("           SYNDICATE REIGN - SYSTEM HEALTH REPORT")
    print(f"           Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # ─────────────────────────────────────────────────────────────────────
    # SECTION 1: INFRASTRUCTURE
    # ─────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  1. INFRASTRUCTURE")
    print("─" * 70)

    # Memory
    mem = run_cmd("free -m")
    print("\n[MEMORY]")
    for line in mem.split("\n"):
        print(f"  {line}")

    # Disk
    disk = run_cmd("df -h /")
    print("\n[DISK]")
    for line in disk.split("\n"):
        print(f"  {line}")

    # Load
    load = run_cmd("uptime")
    print(f"\n[LOAD]\n  {load}")

    # ─────────────────────────────────────────────────────────────────────
    # SECTION 2: SERVICES
    # ─────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  2. SYSTEMD SERVICES")
    print("─" * 70)

    services = ["syndicate-daemon", "syndicate-executor", "syndicate-discord", "syndicate-sentinel"]

    print("\n  {:<25} {:<10} {:<10} {:<10} {:<8}".format("SERVICE", "STATUS", "ENABLED", "MEMORY", "PID"))
    print("  " + "-" * 63)

    for svc in services:
        info = get_service_status(svc)
        status_icon = "✓" if info["status"] == "active" else "✗"
        print(
            f"  {svc:<25} {status_icon} {info['status']:<7} {info['enabled']:<10} {str(info['memory_mb'])+'M':<10} {info['pid']:<8}"
        )

    # ─────────────────────────────────────────────────────────────────────
    # SECTION 3: TIMERS
    # ─────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  3. SCHEDULED TIMERS")
    print("─" * 70)

    timers = run_cmd("systemctl list-timers --no-pager | grep syndicate")
    print(f"\n{timers}")

    # ─────────────────────────────────────────────────────────────────────
    # SECTION 4: DATABASE
    # ─────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  4. DATABASE METRICS")
    print("─" * 70)

    db_path = os.path.expanduser("~/syndicate/data/syndicate.db")
    if os.path.exists(db_path):
        db_size = os.path.getsize(db_path) / 1024 / 1024
        print(f"\n  Database Size: {db_size:.2f} MB")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # LLM Tasks
        print("\n  [LLM TASKS]")
        cursor.execute("SELECT status, COUNT(*) FROM llm_tasks GROUP BY status")
        for row in cursor.fetchall():
            print(f"    {row[0]}: {row[1]}")

        # Stuck tasks
        cursor.execute("SELECT COUNT(*) FROM llm_tasks WHERE status='in_progress'")
        stuck = cursor.fetchone()[0]
        print(f"\n    ⚠ Stuck Tasks: {stuck}")

        # Document Lifecycle
        print("\n  [DOCUMENT LIFECYCLE]")
        cursor.execute("SELECT status, COUNT(*) FROM document_lifecycle GROUP BY status")
        for row in cursor.fetchall():
            print(f"    {row[0]}: {row[1]}")

        # Notion Sync
        cursor.execute("SELECT COUNT(*) FROM notion_sync")
        notion_count = cursor.fetchone()[0]
        print(f"\n  [NOTION SYNC]\n    Total Synced: {notion_count}")

        # System Config
        print("\n  [SYSTEM CONFIG]")
        cursor.execute("SELECT key, value FROM system_config WHERE key IN ('notion_publishing_enabled', 'ai_enabled')")
        for row in cursor.fetchall():
            print(f"    {row[0]}: {row[1]}")

        conn.close()
    else:
        print(f"\n  ✗ Database not found at {db_path}")

    # ─────────────────────────────────────────────────────────────────────
    # SECTION 5: LLM STATUS
    # ─────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  5. LLM STATUS")
    print("─" * 70)

    model_path = os.path.expanduser("~/.cache/syndicate/models/Phi-3-mini-4k-instruct-q4.gguf")
    if os.path.exists(model_path):
        model_size = os.path.getsize(model_path) / 1024 / 1024 / 1024
        print("\n  Model: Phi-3-mini-4k-instruct-q4.gguf")
        print(f"  Size: {model_size:.2f} GB")
        print("  Status: ✓ Available")
    else:
        print("\n  ✗ Model not found")

    llm_provider = os.getenv("LLM_PROVIDER", "not set")
    print(f"  Provider: {llm_provider}")

    # ─────────────────────────────────────────────────────────────────────
    # SECTION 6: ENVIRONMENT
    # ─────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  6. ENVIRONMENT KEYS")
    print("─" * 70)

    keys_to_check = [
        "DISCORD_BOT_TOKEN",
        "DISCORD_APP_ID",
        "NOTION_API_KEY",
        "NOTION_DATABASE_ID",
        "GEMINI_API_KEY",
        "NEWSAPI_KEY",
        "LLM_PROVIDER",
    ]

    print()
    for key in keys_to_check:
        value = os.getenv(key, "")
        if value:
            masked = value[:8] + "..." if len(value) > 10 else value
            print(f"  {key}: ✓ Set ({masked})")
        else:
            print(f"  {key}: ✗ NOT SET")

    # ─────────────────────────────────────────────────────────────────────
    # SECTION 7: OUTPUT DIRECTORY
    # ─────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  7. OUTPUT DIRECTORY")
    print("─" * 70)

    output_dir = Path(os.path.expanduser("~/syndicate/output"))
    if output_dir.exists():
        # Count files by type
        md_files = list(output_dir.glob("**/*.md"))
        today = datetime.now().date()
        today_files = [f for f in md_files if today.strftime("%Y-%m-%d") in f.name]

        print(f"\n  Total MD Files: {len(md_files)}")
        print(f"  Today's Files: {len(today_files)}")

        if today_files:
            print("\n  [TODAY'S FILES]")
            for f in sorted(today_files)[:10]:
                print(f"    - {f.name}")
    else:
        print("\n  ✗ Output directory not found")

    # ─────────────────────────────────────────────────────────────────────
    # SECTION 8: RECENT ERRORS
    # ─────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  8. RECENT ERRORS (Last 10)")
    print("─" * 70)

    errors = run_cmd("journalctl -p err --since '1 hour ago' -n 10 --no-pager 2>/dev/null")
    if errors:
        print(f"\n{errors}")
    else:
        print("\n  ✓ No recent errors")

    # ─────────────────────────────────────────────────────────────────────
    # SUMMARY
    # ─────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)

    # Quick health check
    all_services_up = all(get_service_status(s)["status"] == "active" for s in services)
    llm_available = os.path.exists(model_path)
    db_available = os.path.exists(db_path)

    print(f"\n  Services: {'✓ All Active' if all_services_up else '✗ Some Down'}")
    print(f"  LLM: {'✓ Available' if llm_available else '✗ Missing'}")
    print(f"  Database: {'✓ Available' if db_available else '✗ Missing'}")
    print(f"  Stuck Tasks: {stuck if 'stuck' in dir() else 'N/A'}")

    overall = "HEALTHY" if (all_services_up and llm_available and db_available) else "DEGRADED"
    print(f"\n  Overall Status: {overall}")

    print("\n" + "=" * 70)
    print("                         END OF REPORT")
    print("=" * 70)


if __name__ == "__main__":
    main()
