#!/usr/bin/env python3
"""
Syndicate Pipeline Audit Tool

Comprehensive testing and auditing of the entire pipeline:
- Research module
- Insights extraction
- Task execution
- Frontmatter/tagging system
- Notion publishing (when enabled)

Run with: python scripts/pipeline_audit.py
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print("=" * 60)


def print_result(label: str, status: str, detail: str = ""):
    """Print a test result."""
    icon = "[OK]" if status == "ok" else "[WARN]" if status == "warn" else "[FAIL]"
    print(f"  {icon} {label}")
    if detail:
        for line in detail.split("\n"):
            print(f"      {line}")


def audit_database() -> Dict[str, Any]:
    """Audit database state and integrity."""
    print_section("DATABASE AUDIT")

    from db_manager import get_db

    db = get_db()
    results = {}

    # Check tables and counts
    import sqlite3

    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cursor.fetchall()]

    print(f"  Tables found: {len(tables)}")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        results[table] = count
        if count > 0:
            print(f"    {table}: {count} rows")

    # Check for orphaned records
    print("\n  Checking data integrity...")

    # Check notion_sync paths exist
    cursor.execute("SELECT file_path FROM notion_sync")
    synced_files = [r[0] for r in cursor.fetchall()]
    missing_files = [f for f in synced_files if not Path(f).exists()]
    if missing_files:
        print_result("Notion sync paths", "warn", f"{len(missing_files)} synced files no longer exist")
    else:
        print_result("Notion sync paths", "ok", "All synced files exist")

    # Check document_lifecycle paths
    cursor.execute("SELECT file_path FROM document_lifecycle")
    lifecycle_files = [r[0] for r in cursor.fetchall()]
    missing_lifecycle = [f for f in lifecycle_files if not Path(f).exists()]
    if missing_lifecycle:
        print_result("Lifecycle paths", "warn", f"{len(missing_lifecycle)} lifecycle files no longer exist")
    else:
        print_result("Lifecycle paths", "ok", "All lifecycle files exist")

    conn.close()
    return results


def audit_toggles() -> Dict[str, bool]:
    """Audit feature toggles."""
    print_section("FEATURE TOGGLES")

    from db_manager import get_db

    db = get_db()

    toggles = {
        "notion_publishing": db.is_notion_publishing_enabled(),
        "task_execution": db.is_task_execution_enabled(),
        "insights_extraction": db.is_insights_extraction_enabled(),
    }

    for name, enabled in toggles.items():
        status = "ENABLED" if enabled else "DISABLED"
        print(f"  {name}: {status}")

    return toggles


def audit_frontmatter() -> Dict[str, Any]:
    """Audit frontmatter on output files."""
    print_section("FRONTMATTER AUDIT")

    from main import Config
    from scripts.frontmatter import get_document_status, has_frontmatter

    config = Config()
    output_path = Path(config.OUTPUT_DIR)

    results = {
        "total_files": 0,
        "has_frontmatter": 0,
        "missing_frontmatter": 0,
        "by_status": {},
        "files_missing_fm": [],
    }

    # Find all markdown files
    md_files = list(output_path.glob("**/*.md"))
    results["total_files"] = len(md_files)

    for md_file in md_files:
        if "FILE_INDEX" in md_file.name or "archive" in str(md_file).lower():
            continue

        try:
            content = md_file.read_text(encoding="utf-8")
            if has_frontmatter(content):
                results["has_frontmatter"] += 1
                status = get_document_status(content)
                results["by_status"][status] = results["by_status"].get(status, 0) + 1
            else:
                results["missing_frontmatter"] += 1
                results["files_missing_fm"].append(md_file.name)
        except Exception as e:
            print_result(f"Error reading {md_file.name}", "fail", str(e))

    print(f"  Total markdown files: {results['total_files']}")
    print(f"  With frontmatter: {results['has_frontmatter']}")
    print(f"  Missing frontmatter: {results['missing_frontmatter']}")

    if results["by_status"]:
        print("\n  Status breakdown:")
        for status, count in results["by_status"].items():
            print(f"    {status}: {count}")

    if results["files_missing_fm"]:
        print("\n  Files missing frontmatter:")
        for f in results["files_missing_fm"][:10]:
            print(f"    - {f}")
        if len(results["files_missing_fm"]) > 10:
            print(f"    ... and {len(results['files_missing_fm']) - 10} more")

    return results


def audit_insights() -> Dict[str, Any]:
    """Audit insights extraction system."""
    print_section("INSIGHTS EXTRACTION AUDIT")

    from db_manager import get_db

    db = get_db()

    import sqlite3

    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    results = {
        "entity_count": 0,
        "action_count": 0,
        "entity_types": {},
        "action_types": {},
        "action_statuses": {},
    }

    # Entity insights
    cursor.execute("SELECT COUNT(*) FROM entity_insights")
    results["entity_count"] = cursor.fetchone()[0]

    cursor.execute("SELECT entity_type, COUNT(*) as cnt FROM entity_insights GROUP BY entity_type")
    for row in cursor.fetchall():
        results["entity_types"][row["entity_type"]] = row["cnt"]

    # Action insights
    cursor.execute("SELECT COUNT(*) FROM action_insights")
    results["action_count"] = cursor.fetchone()[0]

    if results["action_count"] > 0:
        cursor.execute("SELECT action_type, COUNT(*) as cnt FROM action_insights GROUP BY action_type")
        for row in cursor.fetchall():
            results["action_types"][row["action_type"]] = row["cnt"]

        cursor.execute("SELECT status, COUNT(*) as cnt FROM action_insights GROUP BY status")
        for row in cursor.fetchall():
            results["action_statuses"][row["status"]] = row["cnt"]

    print(f"  Entity insights: {results['entity_count']}")
    if results["entity_types"]:
        print("    By type:")
        for t, c in sorted(results["entity_types"].items(), key=lambda x: -x[1])[:5]:
            print(f"      {t}: {c}")

    print(f"\n  Action insights: {results['action_count']}")
    if results["action_types"]:
        print("    By type:")
        for t, c in sorted(results["action_types"].items(), key=lambda x: -x[1]):
            print(f"      {t}: {c}")

    if results["action_statuses"]:
        print("    By status:")
        for s, c in results["action_statuses"].items():
            print(f"      {s}: {c}")

    conn.close()
    return results


def audit_task_execution() -> Dict[str, Any]:
    """Audit task execution history."""
    print_section("TASK EXECUTION AUDIT")

    from db_manager import get_db

    db = get_db()

    import sqlite3

    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    results = {
        "total_executions": 0,
        "successful": 0,
        "failed": 0,
        "error_breakdown": {},
    }

    cursor.execute("SELECT COUNT(*) FROM task_execution_log")
    results["total_executions"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM task_execution_log WHERE success = 1")
    results["successful"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM task_execution_log WHERE success = 0")
    results["failed"] = cursor.fetchone()[0]

    # Error breakdown
    cursor.execute("""
        SELECT
            CASE
                WHEN error_message LIKE '%quota%' THEN 'Quota exceeded'
                WHEN error_message LIKE '%All LLM providers failed%' THEN 'LLM provider failure'
                WHEN error_message LIKE '%Unknown action type%' THEN 'Invalid action type'
                WHEN error_message LIKE '%Could not determine%' THEN 'Parse error'
                WHEN error_message IS NULL THEN 'Success'
                ELSE 'Other error'
            END as error_type,
            COUNT(*) as cnt
        FROM task_execution_log
        GROUP BY error_type
    """)
    for row in cursor.fetchall():
        results["error_breakdown"][row["error_type"]] = row["cnt"]

    print(f"  Total executions: {results['total_executions']}")
    print(f"  Successful: {results['successful']}")
    print(f"  Failed: {results['failed']}")

    if results["error_breakdown"]:
        print("\n  Error breakdown:")
        for err, cnt in sorted(results["error_breakdown"].items(), key=lambda x: -x[1]):
            pct = cnt / results["total_executions"] * 100 if results["total_executions"] > 0 else 0
            print(f"    {err}: {cnt} ({pct:.1f}%)")

    # Check for invalid action types
    cursor.execute("""
        SELECT DISTINCT error_message
        FROM task_execution_log
        WHERE error_message LIKE '%Unknown action type%'
    """)
    invalid_types = [r[0] for r in cursor.fetchall()]
    if invalid_types:
        print("\n  Invalid action types found:")
        for err in invalid_types:
            print(f"    - {err}")

    conn.close()
    return results


def audit_notion_sync() -> Dict[str, Any]:
    """Audit Notion sync state."""
    print_section("NOTION SYNC AUDIT")

    from db_manager import get_db

    db = get_db()

    import sqlite3

    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    results = {
        "total_synced": 0,
        "by_type": {},
        "path_issues": [],
    }

    cursor.execute("SELECT COUNT(*) FROM notion_sync")
    results["total_synced"] = cursor.fetchone()[0]

    cursor.execute("SELECT doc_type, COUNT(*) as cnt FROM notion_sync GROUP BY doc_type")
    for row in cursor.fetchall():
        results["by_type"][row["doc_type"] or "unknown"] = row["cnt"]

    # Check for path normalization issues
    cursor.execute("SELECT file_path FROM notion_sync")
    paths = [r[0] for r in cursor.fetchall()]

    relative_paths = [p for p in paths if not (p.startswith("C:") or p.startswith("/"))]
    if relative_paths:
        results["path_issues"] = relative_paths[:5]

    print(f"  Total synced files: {results['total_synced']}")

    if results["by_type"]:
        print("\n  By document type:")
        for t, c in sorted(results["by_type"].items(), key=lambda x: -x[1]):
            print(f"    {t}: {c}")

    if results["path_issues"]:
        print_result("Path normalization", "warn", f"{len(relative_paths)} files have relative paths")
    else:
        print_result("Path normalization", "ok", "All paths are absolute")

    conn.close()
    return results


def audit_schedule() -> Dict[str, Any]:
    """Audit schedule tracker."""
    print_section("SCHEDULE TRACKER AUDIT")

    from db_manager import get_db

    db = get_db()

    import sqlite3

    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT task_name, last_run, frequency, enabled FROM schedule_tracker ORDER BY last_run DESC")
    rows = cursor.fetchall()

    print(f"  Scheduled tasks: {len(rows)}")
    print("\n  Task status:")
    for row in rows:
        last_run = row["last_run"][:16] if row["last_run"] else "Never"
        enabled = "ON" if row["enabled"] else "OFF"
        print(f"    [{enabled}] {row['task_name']}: {last_run} ({row['frequency']})")

    conn.close()
    return {"count": len(rows)}


def run_full_audit():
    """Run the complete pipeline audit."""
    print("\n" + "=" * 60)
    print("       SYNDICATE PIPELINE AUDIT")
    print(f"       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = {}

    try:
        results["toggles"] = audit_toggles()
        results["database"] = audit_database()
        results["frontmatter"] = audit_frontmatter()
        results["insights"] = audit_insights()
        results["task_execution"] = audit_task_execution()
        results["notion_sync"] = audit_notion_sync()
        results["schedule"] = audit_schedule()
    except Exception as e:
        print(f"\n[ERROR] Audit failed: {e}")
        import traceback

        traceback.print_exc()
        return None

    # Summary
    print_section("AUDIT SUMMARY")

    issues = []

    # Check for critical issues
    if results["frontmatter"]["missing_frontmatter"] > 0:
        issues.append(f"- {results['frontmatter']['missing_frontmatter']} files missing frontmatter")

    if results["insights"]["action_count"] == 0:
        issues.append("- No action insights in database (actions may be getting deleted after execution)")

    if results["task_execution"]["failed"] > results["task_execution"]["successful"]:
        issues.append(
            f"- More failed tasks ({results['task_execution']['failed']}) than successful ({results['task_execution']['successful']})"
        )

    fm_status = results["frontmatter"]["by_status"]
    if fm_status.get("published", 0) == 0 and fm_status:
        issues.append("- No documents have 'published' status (pipeline may be stuck)")

    if issues:
        print("  ISSUES FOUND:")
        for issue in issues:
            print(f"    {issue}")
    else:
        print("  No critical issues found.")

    return results


def run_cleanup(dry_run: bool = True) -> Dict[str, int]:
    """Remove orphan database records where files no longer exist."""
    print_section("ORPHAN CLEANUP")

    if dry_run:
        print("  [DRY RUN] No changes will be made. Use --cleanup --execute to apply.")

    import sqlite3

    from db_manager import get_db

    db = get_db()
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()

    results = {"notion_sync": 0, "document_lifecycle": 0}

    # Clean orphan notion_sync records
    cursor.execute("SELECT file_path FROM notion_sync")
    synced_files = [r[0] for r in cursor.fetchall()]
    orphan_syncs = [f for f in synced_files if not Path(f).exists()]

    print(f"\n  Orphan notion_sync records: {len(orphan_syncs)}")
    if orphan_syncs and not dry_run:
        for path in orphan_syncs:
            cursor.execute("DELETE FROM notion_sync WHERE file_path = ?", (path,))
        conn.commit()
        print(f"    Deleted {len(orphan_syncs)} orphan sync records")
    results["notion_sync"] = len(orphan_syncs)

    # Clean orphan document_lifecycle records
    cursor.execute("SELECT file_path FROM document_lifecycle")
    lifecycle_files = [r[0] for r in cursor.fetchall()]
    orphan_lifecycle = [f for f in lifecycle_files if not Path(f).exists()]

    print(f"  Orphan document_lifecycle records: {len(orphan_lifecycle)}")
    if orphan_lifecycle and not dry_run:
        for path in orphan_lifecycle:
            cursor.execute("DELETE FROM document_lifecycle WHERE file_path = ?", (path,))
        conn.commit()
        print(f"    Deleted {len(orphan_lifecycle)} orphan lifecycle records")
    results["document_lifecycle"] = len(orphan_lifecycle)

    conn.close()

    if dry_run:
        print(f"\n  Total orphan records to remove: {sum(results.values())}")
    else:
        print(f"\n  Total orphan records removed: {sum(results.values())}")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="pipeline_audit", description="Audit and cleanup the Syndicate pipeline")
    parser.add_argument("--cleanup", action="store_true", help="Run orphan record cleanup (dry run by default)")
    parser.add_argument("--execute", action="store_true", help="Actually execute cleanup (otherwise dry run)")

    args = parser.parse_args()

    if args.cleanup:
        run_cleanup(dry_run=not args.execute)
    else:
        run_full_audit()
