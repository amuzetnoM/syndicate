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
Syndicate CLI
Unified entry point with intelligent report management.
Runs all analysis with automatic redundancy control.

Default mode: Autonomous daemon that runs analysis every 4 hours.
Use --once for single execution, or --interactive for menu.
"""

import argparse
import os
import signal
import sys
import time
from datetime import date, datetime

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Task execution configuration
MAX_RETRIES = 3  # Max retries before marking task as failed

# Executor daemon mode - default to enabled when not explicitly disabled.
# Use GOST_DETACHED_EXECUTOR=0 to force inline executor for testing.
USE_DETACHED_EXECUTOR = os.environ.get("GOST_DETACHED_EXECUTOR", "1") != "0"


def spawn_executor_daemon() -> bool:
    """
    Spawn the task executor as a detached background process.

    The executor daemon runs independently and survives main process shutdown.
    It handles orphan recovery and graceful task completion.

    Returns:
        True if spawn successful or executor already running
    """
    try:
        from scripts.executor_daemon import is_executor_running, spawn_executor_subprocess

        if is_executor_running():
            print("[DAEMON] Task executor already running")
            return True

        pid = spawn_executor_subprocess(detach=True)
        if pid:
            print(f"[DAEMON] Spawned task executor daemon (PID: {pid})")
            return True
        else:
            print("[DAEMON] Failed to spawn executor daemon")
            return False
    except ImportError:
        print("[DAEMON] Executor daemon not available, using inline execution")
        return False
    except Exception as e:
        print(f"[DAEMON] Executor spawn error: {e}")
        return False


def ensure_venv():
    """
    Ensure we're running inside the virtual environment.
    If not, re-execute this script with the venv Python.
    """
    # Check if already in venv
    if hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix):
        return  # Already in venv

    # Look for venv directories
    venv_path = "/mnt/disk/.venv"
    venv_python = None

    if os.path.isdir(venv_path):
        # Windows vs Unix paths
        if sys.platform == "win32":
            candidate = os.path.join(venv_path, "Scripts", "python.exe")
        else:
            candidate = os.path.join(venv_path, "bin", "python")

        if os.path.isfile(candidate):
            venv_python = candidate

    if venv_python:
        print(
            f"[VENV] Activating virtual environment: {venv_path}"
        )
        # Re-execute with venv python
        os.execv(venv_python, [venv_python] + sys.argv)
    else:
        print(f"[WARN] Virtual environment not found at {venv_path}. Running with system Python.")
        print("       Please ensure the virtual environment is correctly set up.")


# Ensure venv before importing project modules
ensure_venv()

# Start metrics server early to ensure scrape targets are available
try:
    from scripts.metrics_server import start_metrics_server
    start_metrics_server()
    print('[METRICS] metrics server started')
except Exception as e:
    print(f'[METRICS] could not start metrics server: {e}')

# Deploy Grafana dashboard if credentials are present
try:
    from scripts.deploy_grafana_dashboard import deploy as deploy_grafana
    deployed = deploy_grafana()
    if deployed:
        print('[GRAFANA] dashboard deployed')
    else:
        print('[GRAFANA] dashboard deploy skipped or failed')
except Exception as e:
    print(f'[GRAFANA] error during dashboard deploy: {e}')


def find_venv_python() -> str | None:
    """Return the preferred venv Python executable path if available, else None."""
    venv_dirs = ["venv312", "venv", ".venv"]
    for venv_name in venv_dirs:
        venv_path = os.path.join(PROJECT_ROOT, venv_name)
        if os.path.isdir(venv_path):
            if sys.platform == "win32":
                candidate = os.path.join(venv_path, "Scripts", "python.exe")
            else:
                candidate = os.path.join(venv_path, "bin", "python")
            if os.path.isfile(candidate):
                return candidate
    return None


def get_python_executable() -> str:
    """Return the Python executable to use for subprocesses (prefer venv)."""
    venv_python = find_venv_python()
    if venv_python:
        return venv_python
    return sys.executable


import schedule  # noqa: E402

from db_manager import get_db  # noqa: E402

# Banner
BANNER = r"""
                                          ___           ___
  _________ _________ _________ _________ ____ ____ ____ ____
||       |||       |||       |||       |||G |||O |||L |||D ||
||_______|||_______|||_______|||_______|||__|||__|||__|||__||
|/_______\|/_______\|/_______\|/_______\|/__\|/__\|/__\|/__\|
 _________ ____ ____ ____ ____ ____ ____ ____ ____
||       |||S |||T |||A |||N |||D |||A |||R |||D ||
||_______|||__|||__|||__|||__|||__|||__|||__|||__||
|/_______\|/__\|/__\|/__\|/__\|/__\|/__\|/__\|/__\|

          PRECIOUS METALS INTELLIGENCE COMPLEX
"""


def print_banner():
    print(BANNER)


def print_status():
    """Print current system status."""
    db = get_db()
    info = db.get_current_period_info()
    missing = db.get_missing_reports()
    stats = db.get_statistics()

    print("\n" + "=" * 60)
    print("                    SYSTEM STATUS")
    print("=" * 60)
    print(f"  Date: {info['today']}  |  Week {info['week']}  |  {info['month_period']}")
    print("-" * 60)
    print(f"  Total Journals: {stats['total_journals']}")
    print(f"  Weekly Reports: {stats['weekly_reports']}")
    print(f"  Monthly Reports: {stats['monthly_reports']}")
    print(f"  Yearly Reports: {stats['yearly_reports']}")
    print("-" * 60)
    print("  Today's Status:")
    print(f"    Daily Journal:   {'[OK] EXISTS' if not missing['daily_journal'] else '[--] MISSING'}")
    print(f"    Pre-Market Plan: {'[OK] EXISTS' if not missing['premarket_plan'] else '[--] MISSING'}")
    print(f"    Weekly Report:   {'[OK] EXISTS' if not missing['weekly_report'] else '[--] MISSING'}")
    print(f"    Monthly Report:  {'[OK] EXISTS' if not missing['monthly_report'] else '[--] MISSING'}")
    print(f"    Yearly Report:   {'[OK] EXISTS' if not missing['yearly_report'] else '[--] MISSING'}")
    print("-" * 60)

    # Show schedule status
    print("  Scheduled Tasks:")
    try:
        schedules = db.get_schedule_status()
        for sched in schedules:
            status = "[READY]" if sched["should_run"] else "[DONE] "
            freq = sched["frequency"].upper()[:3]
            last = sched["last_run"][:16] if sched["last_run"] else "Never"
            print(f"    {status} {sched['task_name']:<25} ({freq}) Last: {last}")
    except Exception as e:
        print(f"    (Schedule info unavailable: {e})")

    print("=" * 60 + "\n")


def run_daily(no_ai: bool = False) -> bool:
    """Run the daily journal via main.py."""
    print("\n>> Running Daily Journal Analysis...\n")
    cmd_parts = [get_python_executable(), "main.py", "--once"]
    if no_ai:
        cmd_parts.append("--no-ai")
    return os.system(" ".join(cmd_parts)) == 0


def run_weekly(no_ai: bool = False) -> bool:
    """Run the weekly rundown via split_reports.py."""
    print("\n>> Generating Weekly Report...\n")
    cmd_parts = [get_python_executable(), "scripts/split_reports.py", "--mode", "weekly", "--once"]
    if no_ai:
        cmd_parts.append("--no-ai")
    return os.system(" ".join(cmd_parts)) == 0


def run_monthly(no_ai: bool = False) -> bool:
    """Run the monthly report via split_reports.py."""
    print("\n>> Generating Monthly Report...\n")
    cmd_parts = [get_python_executable(), "scripts/split_reports.py", "--mode", "monthly", "--once"]
    if no_ai:
        cmd_parts.append("--no-ai")
    return os.system(" ".join(cmd_parts)) == 0


def run_yearly(no_ai: bool = False) -> bool:
    """Run the yearly report via split_reports.py."""
    print("\n>> Generating Yearly Report...\n")
    cmd_parts = [get_python_executable(), "scripts/split_reports.py", "--mode", "yearly", "--once"]
    if no_ai:
        cmd_parts.append("--no-ai")
    return os.system(" ".join(cmd_parts)) == 0


def run_premarket(no_ai: bool = False) -> bool:
    """Run the pre-market plan via pre_market.py."""
    print("\n>> Generating Pre-Market Plan...\n")
    cmd_parts = [get_python_executable(), "scripts/pre_market.py"]
    if no_ai:
        cmd_parts.append("--no-ai")
    return os.system(" ".join(cmd_parts)) == 0


def run_all(no_ai: bool = False, force: bool = False):
    """
    Run complete analysis with intelligent redundancy control.

    1. Always runs daily journal (updates today's entry)
    2. Checks and generates pre-market plan if missing
    3. Checks and generates weekly report if missing (on weekends or if forced)
    4. Checks and generates monthly report if missing for current month
    5. Checks and generates yearly report if missing for current year
    """
    db = get_db()
    today = date.today()
    iso_cal = today.isocalendar()

    print("\n" + "=" * 60)
    print("              RUNNING FULL ANALYSIS")
    print("=" * 60)

    results = {}

    # 1. Daily journal (check if already done in this cycle)
    print("\n[1/5] DAILY JOURNAL")
    print("-" * 40)
    if db.has_journal_for_date(today.isoformat()) and not force:
        # Journal exists - only update if it's been more than 4 hours
        last_update = db.get_journal_last_update(today.isoformat())
        if last_update:
            from datetime import datetime, timedelta

            last_dt = datetime.fromisoformat(last_update) if isinstance(last_update, str) else last_update
            if datetime.now() - last_dt < timedelta(hours=4):
                print("  [SKIP] Daily journal recently updated (within 4 hours)")
                results["daily"] = True
            else:
                results["daily"] = run_daily(no_ai=no_ai)
        else:
            results["daily"] = run_daily(no_ai=no_ai)
    else:
        results["daily"] = run_daily(no_ai=no_ai)

    # 2. Pre-market plan (if not already done today)
    print("\n[2/5] PRE-MARKET PLAN")
    print("-" * 40)
    if not db.has_premarket_for_date(today.isoformat()) or force:
        results["premarket"] = run_premarket(no_ai=no_ai)
    else:
        print("  [SKIP] Pre-market plan already exists for today")
        results["premarket"] = True

    # 3. Weekly report (on weekends or if forced or missing)
    print("\n[3/5] WEEKLY REPORT")
    print("-" * 40)
    is_weekend = iso_cal[2] >= 6  # Saturday = 6, Sunday = 7
    if not db.has_weekly_report(today.year, iso_cal[1]) and (is_weekend or force):
        results["weekly"] = run_weekly(no_ai=no_ai)
    elif db.has_weekly_report(today.year, iso_cal[1]):
        print(f"  [SKIP] Weekly report for Week {iso_cal[1]} already exists")
        results["weekly"] = True
    else:
        print("  [SKIP] Not weekend. Weekly reports generated on Sat/Sun")
        results["weekly"] = True

    # 4. Monthly report (check if exists for current month)
    print("\n[4/5] MONTHLY REPORT")
    print("-" * 40)
    if not db.has_monthly_report(today.year, today.month) or force:
        print(f"  Generating report for {today.year}-{today.month:02d}...")
        results["monthly"] = run_monthly(no_ai=no_ai)
    else:
        print(f"  [SKIP] Monthly report for {today.year}-{today.month:02d} already exists")
        results["monthly"] = True

    # 5. Yearly report (check if exists for current year)
    print("\n[5/5] YEARLY REPORT")
    print("-" * 40)
    if not db.has_yearly_report(today.year) or force:
        print(f"  Generating report for {today.year}...")
        results["yearly"] = run_yearly(no_ai=no_ai)
    else:
        print(f"  [SKIP] Yearly report for {today.year} already exists")
        results["yearly"] = True

    # Summary
    print("\n" + "=" * 60)
    print("                    SUMMARY")
    print("=" * 60)
    for task, success in results.items():
        status = "[OK]" if success else "[FAIL]"
        print(f"  {task.upper():15} {status}")
    print("=" * 60 + "\n")

    return all(results.values())


# Global flag for graceful shutdown
_shutdown_requested = False


def _signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global _shutdown_requested
    print("\n\n  [SHUTDOWN] Signal received, stopping gracefully...")
    _shutdown_requested = True


def run_daemon(no_ai: bool = False, interval_hours: int = 0, interval_minutes: int = 1):
    """
    Run Syndicate as an autonomous daemon.
    Executes analysis immediately, then at specified intervals.

    Args:
        no_ai: Disable AI-generated content
        interval_hours: Hours between analysis runs (legacy, use 0 with interval_minutes)
        interval_minutes: Minutes between analysis runs (default: 1 for real-time)
    """
    global _shutdown_requested

    # Register signal handlers
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # Determine effective interval
    if interval_hours > 0:
        interval_display = f"{interval_hours} hour(s)"
        use_minutes = False
        interval_value = interval_hours
    else:
        interval_display = f"{interval_minutes} minute(s)"
        use_minutes = True
        interval_value = interval_minutes

    print("\n" + "=" * 60)
    print("       GOLD STANDARD - AUTONOMOUS MODE")
    print("=" * 60)
    print(f"  Interval: Every {interval_display}")
    print(f"  AI Mode:  {'Disabled' if no_ai else 'Enabled'}")
    print("  Press Ctrl+C to shutdown gracefully")
    print("=" * 60 + "\n")

    # Import insights and task systems
    try:
        from scripts.file_organizer import FileOrganizer as _FileOrganizer  # noqa: F401
        from scripts.insights_engine import InsightsExtractor as _InsightsExtractor  # noqa: F401
        from scripts.task_executor import TaskExecutor as _TaskExecutor  # noqa: F401

        insights_available = True
        print("[DAEMON] Insights & Task systems loaded")
        # If configured, attempt to spawn the detached executor daemon for robust task execution
        if USE_DETACHED_EXECUTOR:
            spawned = spawn_executor_daemon()
            if spawned:
                print("[DAEMON] Detached executor active or spawned successfully")
            else:
                print("[DAEMON] Detached executor not available; will run inline")
    except ImportError as e:
        insights_available = False
        print(f"[DAEMON] Insights systems not available: {e}")

    # STARTUP RECOVERY: Reset stuck tasks and resume from where we left off
    try:
        from db_manager import DatabaseManager

        db = DatabaseManager()

        # Reset any tasks stuck in 'in_progress' from previous crash
        reset_count = db.reset_stuck_actions(max_age_hours=24)
        if reset_count > 0:
            print(f"[DAEMON] Recovered {reset_count} stuck tasks from previous session")

        # Check for ready tasks on startup
        ready_count = len(db.get_ready_actions(limit=None) or [])
        if ready_count > 0:
            print(f"[DAEMON] Found {ready_count} tasks ready for immediate execution")

        # Check scheduled tasks
        scheduled = db.get_scheduled_actions()
        if scheduled:
            print(f"[DAEMON] {len(scheduled)} tasks scheduled for future execution")
    except Exception as e:
        print(f"[DAEMON] Startup recovery check failed: {e}")

    # Run immediately on startup
    print("[DAEMON] Running initial analysis cycle...\n")
    run_all(no_ai=no_ai, force=False)

    # Run post-analysis tasks if available
    if insights_available and not no_ai:
        _run_post_analysis_tasks()

    # Schedule recurring runs
    if use_minutes:
        schedule.every(interval_value).minutes.do(
            _daemon_cycle, no_ai=no_ai, run_tasks=insights_available and not no_ai
        )
    else:
        schedule.every(interval_value).hours.do(_daemon_cycle, no_ai=no_ai, run_tasks=insights_available and not no_ai)

    print(f"\n[DAEMON] Next run scheduled in {interval_display}")
    print("[DAEMON] System is now running autonomously...\n")

    # Main loop
    while not _shutdown_requested:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            print(f"[DAEMON] Error in main loop: {e}")
            time.sleep(5)

    print("\n[DAEMON] Shutdown complete. Goodbye!\n")


def _daemon_cycle(no_ai: bool = False, run_tasks: bool = True):
    """
    Single daemon cycle:
    1. Run analysis
    2. Extract insights
    3. Execute pending tasks
    4. Organize files
    """
    print(f"\n[DAEMON] Starting cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Run main analysis
    run_all(no_ai=no_ai, force=False)

    # Run post-analysis tasks
    if run_tasks:
        _run_post_analysis_tasks()


def _run_post_analysis_tasks(force_inline: bool = False, wait_for_completion: bool = False, max_wait_seconds: int = 300, poll_interval: int = 2, wait_forever: bool = False):
    """
    Run insights extraction, task execution, file organization, and Notion publishing.
    - force_inline: if True, do not spawn detached executor and run tasks inline
    - wait_for_completion: if True, wait (with timeout) for all ready tasks to be executed and publishing to complete
    """
    try:
        from pathlib import Path

        from main import Config, create_llm_provider, setup_logging
        from scripts.file_organizer import FileOrganizer
        from scripts.insights_engine import InsightsExtractor
        from scripts.task_executor import TaskExecutor

        # Use the full Config for proper LLM provider initialization
        config = Config()

        # Set up proper logger
        logger = setup_logging(config)

        # Get database for schedule tracking
        from db_manager import get_db

        db = get_db()

        # Use unified LLM provider (local LLM or Gemini)
        model = create_llm_provider(config, logger)
        if model:
            logger.info(f"[DAEMON] Using LLM provider: {model.name}")

        def run_inline_tasks_once():
            """Execute ready actions inline and return (success_count, fail_count, notion_count)"""
            try:
                extractor = InsightsExtractor(config, logger, model)
            except Exception:
                # InsightsExtractor may not be available - fall back to a minimal executor
                extractor = None

            ready_actions = db.get_ready_actions(limit=None)
            if not ready_actions:
                return 0, 0, 0

            claimed_actions = []
            from scripts.insights_engine import ActionInsight

            for action_dict in ready_actions:
                action_id = action_dict["action_id"]
                if db.claim_action(action_id, worker_id="daemon-inline"):
                    action = ActionInsight(
                        action_id=action_id,
                        action_type=action_dict["action_type"],
                        title=action_dict["title"],
                        description=action_dict.get("description", ""),
                        priority=action_dict.get("priority", "medium"),
                        status="pending",
                        source_report=action_dict.get("source_report", ""),
                        source_context=action_dict.get("source_context", ""),
                        deadline=action_dict.get("deadline"),
                        scheduled_for=action_dict.get("scheduled_for"),
                        retry_count=action_dict.get("retry_count", 0),
                        last_error=action_dict.get("last_error"),
                    )
                    if extractor:
                        extractor.action_queue.append(action)
                    claimed_actions.append(action_id)

            if not claimed_actions:
                return 0, 0, 0

            executor = TaskExecutor(config, logger, model, extractor)
            results = executor.execute_all_pending(max_tasks=None)

            success_count = 0
            fail_count = 0
            for result in results:
                db.log_task_execution(
                    result.action_id,
                    result.success,
                    str(result.result_data),
                    result.execution_time_ms,
                    result.error_message,
                    str(result.artifacts) if result.artifacts else None,
                )

                if result.success:
                    db.update_action_status(result.action_id, "completed", str(result.result_data))
                    success_count += 1
                else:
                    retry_count = db.increment_retry_count(result.action_id, result.error_message)
                    lmax = int(os.getenv("LLM_MAX_RETRIES", str(MAX_RETRIES)))
                    if lmax >= 0 and retry_count >= lmax:
                        db.update_action_status(result.action_id, "failed", f"Max retries exceeded: {result.error_message}")
                        fail_count += 1
                    else:
                        db.release_action(result.action_id, reason=f"retry_{retry_count}")

            notion_count = executor.stats.get("notion_published", 0)
            return success_count, fail_count, notion_count

        # 1. Extract insights from today's reports (DAILY)
        def run_insights_once(ignore_schedule: bool = False) -> int:
            """Run insights extraction and persist actions. Returns number of actions created."""
            if not db.is_insights_extraction_enabled():
                print("[DAEMON] ⏸️  Insights extraction DISABLED via toggle")
                return 0

            if not ignore_schedule and not db.should_run_task("insights_extraction"):
                print("[DAEMON] Insights extraction already done today, skipping")
                return 0

            print("[DAEMON] Extracting insights from reports...")
            try:
                extractor = InsightsExtractor(config, logger, model)
                reports_dir = Path(config.OUTPUT_DIR) / "reports"
                entities, actions = extractor.process_all_reports(reports_dir)

                # Save insights to database
                for entity in entities:
                    db.save_entity_insight(
                        entity.entity_name,
                        entity.entity_type,
                        entity.context,
                        entity.relevance_score,
                        entity.source_report,
                        str(entity.metadata),
                    )

                for action in actions:
                    db.save_action_insight(
                        action.action_id,
                        action.action_type,
                        action.title,
                        action.description,
                        action.priority,
                        action.status,
                        action.source_report,
                        action.source_context,
                        action.deadline,
                        getattr(action, "scheduled_for", None),
                        str(action.metadata),
                    )

                print(f"[DAEMON] Extracted {len(entities)} entities, {len(actions)} actions")
                # Mark the daily task run if not forced-ignoring schedule
                if not ignore_schedule:
                    db.mark_task_run("insights_extraction")
                return len(actions)
            except Exception as e:
                logger.debug(f"Insights extraction failed: {e}")
                return 0

        # Initial run (obey schedule)
        initial_actions = run_insights_once(ignore_schedule=False)

        # 2. Execute READY tasks with atomic claim/release pattern
        # Tasks execute when: scheduled_for <= now OR scheduled_for IS NULL
        if not db.is_task_execution_enabled():
            print("[DAEMON] ⏸️  Task execution DISABLED via toggle")
        elif db.is_task_execution_enabled():
            # Allow task execution even if no AI provider is available. Some tasks
            # don't require an LLM (data fetches, monitoring, calculations) and
            # should still run. Individual handlers should check self.model as needed.
            if model is None:
                print("[DAEMON] Checking for ready-to-execute tasks (no AI provider; AI tasks will be skipped)...")
            else:
                print("[DAEMON] Checking for ready-to-execute tasks...")

            # Get system health first
            try:
                health = db.get_system_health()
                ready_count = health["tasks"].get("ready_now", 0)
                future_count = health["tasks"].get("scheduled_future", 0)
                stuck_count = health["tasks"].get("stuck_in_progress", 0)

                if stuck_count > 0:
                    print(f"[DAEMON] ⚠️  {stuck_count} stuck tasks detected, recovering...")
                    db.reset_stuck_actions(max_age_hours=1)

                print(f"[DAEMON] Queue status: {ready_count} ready, {future_count} scheduled")
            except Exception as e:
                print(f"[DAEMON] Health check failed: {e}")

            # Decide whether to run inline or spawn detached executor
            use_detached = USE_DETACHED_EXECUTOR and not force_inline
            if use_detached:
                print("[DAEMON] Using detached executor daemon mode...")
                if spawn_executor_daemon():
                    print("[DAEMON] Task execution delegated to executor daemon")
                    # Skip inline execution when executor daemon is handling tasks
                    pass
                else:
                    print("[DAEMON] Falling back to inline execution...")
                    sc, fc, nc = run_inline_tasks_once()
                    print(f"[DAEMON] ✅ Completed: {sc} | ❌ Failed: {fc} | 📤 Published: {nc}")
                    # Run initial publishing pass
                    p_pub, p_skip_sched, p_skip_status = run_publishing_once()
                    if p_pub > 0:
                        print(f"[DAEMON] Published {p_pub} documents to Notion (initial)")
                        # If requested, wait (bounded) or wait_forever to re-run execution+publishing until no ready tasks or new insights
                    if wait_forever:
                        print("[DAEMON] Wait-forever requested: will block until no tasks, no in-progress work, no new insights, and no new publications (indefinitely)")
                        while True:
                            health = db.get_system_health()
                            ready_now = health.get("tasks", {}).get("ready_now", 0)
                            in_progress = health.get("tasks", {}).get("in_progress", 0) or health.get("tasks", {}).get("stuck_in_progress", 0)

                            # If tasks exist, execute them
                            if ready_now > 0:
                                sc2, fc2, nc2 = run_inline_tasks_once()
                                print(f"[DAEMON] ✅ Completed (forever-wait): {sc2} | ❌ Failed: {fc2} | 📤 Published: {nc2}")

                            # Re-run publishing to pick up newly-created docs
                            p_pub2, _, _ = run_publishing_once()
                            if p_pub2 > 0:
                                print(f"[DAEMON] Published {p_pub2} new documents during wait loop")

                            # Re-run insights extraction (force) to detect new actions produced by recent published docs or changes
                            new_actions = run_insights_once(ignore_schedule=True)
                            if new_actions > 0:
                                print(f"[DAEMON] Insights extraction produced {new_actions} new actions (forever-wait) -- continuing loop")

                            # Refresh health
                            health = db.get_system_health()
                            ready_now = health.get("tasks", {}).get("ready_now", 0)
                            in_progress = health.get("tasks", {}).get("in_progress", 0) or health.get("tasks", {}).get("stuck_in_progress", 0)

                            if ready_now == 0 and in_progress == 0 and p_pub2 == 0 and new_actions == 0:
                                print("[DAEMON] No ready/in-progress tasks, no new insights, and no new publications; finishing wait-forever loop")
                                break

                            time.sleep(poll_interval)

                    elif wait_for_completion:
                        start_ts = time.time()
                        while time.time() - start_ts < max_wait_seconds:
                            health = db.get_system_health()
                            ready_now = health.get("tasks", {}).get("ready_now", 0)
                            in_progress = health.get("tasks", {}).get("in_progress", 0) or health.get("tasks", {}).get("stuck_in_progress", 0)

                            if ready_now == 0 and in_progress == 0:
                                print("[DAEMON] No ready or in-progress tasks remain; finishing wait loop")
                                break

                            print(f"[DAEMON] Waiting for tasks to finish: ready={ready_now}, in_progress={in_progress} (timeout in {int(max_wait_seconds - (time.time() - start_ts))}s)")

                            # If there are ready tasks, execute them inline (deterministic)
                            if ready_now > 0:
                                sc2, fc2, nc2 = run_inline_tasks_once()
                                print(f"[DAEMON] ✅ Completed (wait-loop): {sc2} | ❌ Failed: {fc2} | 📤 Published: {nc2}")

                            # Re-run publishing to pick up newly-created docs
                            p_pub2, _, _ = run_publishing_once()
                            if p_pub2 > 0:
                                print(f"[DAEMON] Published {p_pub2} new documents during wait loop")

                            time.sleep(poll_interval)

                        else:
                            print(f"[DAEMON] Wait-for-completion timed out after {max_wait_seconds}s; some tasks may remain")
            else:
                if force_inline:
                    print("[DAEMON] Forcing inline task execution for deterministic single-run behavior")
                else:
                    print("[DAEMON] ⚠️  Using inline executor (deprecated for production)")
                    print("[DAEMON] ℹ️  Set GOST_DETACHED_EXECUTOR=1 or use executor_daemon.py")
                sc, fc, nc = run_inline_tasks_once()
                print(f"[DAEMON] ✅ Completed: {sc} | ❌ Failed: {fc} | 📤 Published: {nc}")


            # Show scheduled tasks info
            scheduled = db.get_scheduled_actions()
            if scheduled:
                print(f"[DAEMON] {len(scheduled)} tasks scheduled for future execution")
        else:
            print("[DAEMON] No AI model available, skipping task execution")

        # 3. Organize files (runs every cycle - lightweight)
        print("[DAEMON] Organizing files...")
        organizer = FileOrganizer(config, logger)
        org_results = organizer.run_maintenance(archive_days=7)
        print(f"[DAEMON] Organized {org_results['organized']} files, archived {org_results['archived']}")

        # 4. Apply frontmatter to all output files (runs every cycle - lightweight)
        print("[DAEMON] Applying frontmatter tags...")
        try:
            from scripts.frontmatter import add_frontmatter, has_frontmatter

            output_path = Path(config.OUTPUT_DIR)
            reports_path = output_path / "reports"
            frontmatter_count = 0

            # Process all markdown files in output directory
            for md_file in (
                list(output_path.glob("*.md")) + list(reports_path.glob("*.md")) + list(reports_path.glob("**/*.md"))
            ):
                try:
                    content = md_file.read_text(encoding="utf-8")

                    # Skip if already has frontmatter
                    if has_frontmatter(content):
                        continue

                    # Detect if AI was used by checking content patterns
                    # AI-generated content typically has these markers
                    ai_markers = [
                        # Journal/Report markers
                        "## 1. Market Context",
                        "## 2. Asset-Specific Analysis",
                        "## 3. Sentiment Summary",
                        "## 4. Strategic Thesis",
                        "## 5. Setup Scan",
                        "## 6. Scenario Probability",
                        "## 7. Risk Management",
                        "## 8. Algo Self-Reflection",
                        "**Bias: ",
                        "**Primary Thesis:",
                        # Pre-market markers
                        "## 1. Strategic Bias",
                        "## 2. Key Risk",
                        "## 3. Critical Events",
                        "## 4. Trade Management",
                        "## 5. Key Levels",
                        "**Overall Bias:**",
                        "**Entry Zone**",
                        "**Stop Loss**",
                    ]
                    ai_processed = any(marker in content for marker in ai_markers)

                    # Also check for NO AI markers
                    # Note: include closing bracket for '[PENDING AI]' to avoid accidental matches
                    no_ai_markers = ["[NO AI MODE]", "AI disabled", "no AI", "skeleton report", "[PENDING AI]"]
                    if any(marker.lower() in content.lower() for marker in no_ai_markers):
                        ai_processed = False

                    # Previous conservative status decision (kept for DB default)
                    determined_status = "in_progress" if ai_processed else "draft"

                    # Add frontmatter allowing generator to auto-promote when appropriate (e.g., Pre-Market/journal)
                    updated = add_frontmatter(content, md_file.name, status=None, ai_processed=ai_processed)
                    md_file.write_text(updated, encoding="utf-8")
                    frontmatter_count += 1

                    # Register in lifecycle database with actual status from the written file
                    try:
                        from scripts.frontmatter import get_document_status
                        doc_type = "journal" if "Journal_" in md_file.name else "reports"
                        actual_status = get_document_status(updated)
                        db.register_document(str(md_file), doc_type, status=actual_status)
                    except Exception:
                        pass  # DB registration is optional

                except Exception as fm_err:
                    logger.debug(f"Frontmatter failed for {md_file.name}: {fm_err}")

            if frontmatter_count > 0:
                print(f"[DAEMON] Applied frontmatter to {frontmatter_count} files")
        except ImportError:
            print("[DAEMON] Frontmatter module not available, skipping")
        except Exception as fm_err:
            print(f"[DAEMON] Frontmatter error: {fm_err}")

        # 5. Publish to Notion with TYPE-AWARE SCHEDULING
        # Different doc types have different sync frequencies:
        # - journal, premarket, research: EVERY CYCLE (daily content)
        # - weekly reports: WEEKLY
        # - monthly reports: MONTHLY
        # - yearly reports: YEARLY
        def run_publishing_once():
                    if not db.is_notion_publishing_enabled():
                        print("[DAEMON] ⏸️  Notion publishing DISABLED via toggle")
                        return 0, 0, 0
                    print("[DAEMON] Publishing to Notion...")
                    try:
                        from scripts.frontmatter import is_ready_for_sync
                        from scripts.notion_publisher import NotionPublisher

                        publisher = NotionPublisher()
                        output_path = Path(config.OUTPUT_DIR)
                        reports_path = output_path / "reports"
                        research_path = output_path / "research"

                        today = date.today()
                        iso_cal = today.isocalendar()

                        # Track results
                        published = 0
                        skipped_schedule = 0
                        skipped_status = 0
                        failed = 0

                        # Define document type schedules
                        def should_sync_doc(filepath: Path, doc_type: str) -> bool:
                            """Check if document should be synced based on type-aware schedule."""
                            filename = filepath.name.lower()

                            # EXCLUDED from Notion sync - internal task outputs
                            excluded_patterns = [
                                "monitor_",
                                "data_fetch_",
                                "calc_",
                                "code_",
                                "_act-",  # Action task outputs (e.g., research_ACT-20251203-0001)
                                "act-",  # Action task files
                                "file_index",  # Index files
                                "digest_",  # Automatically generated daily digests
                                "digests/",  # Files under the digests folder
                            ]
                            if any(p in filename for p in excluded_patterns):
                                return False

                            # Daily documents - always sync if ready
                            daily_patterns = [
                                "journal_",
                                "premarket_",
                                "pre_market_",
                                "research_",
                                "news_scan_",
                                "catalyst",
                                "economic_",
                                "calendar_",
                            ]
                            if any(p in filename for p in daily_patterns):
                                return True

                            # Weekly reports - only on weekends or if not synced this week
                            if "weekly_" in filename or "rundown_" in filename:
                                sync_key = f"notion_sync_weekly_{today.year}_{iso_cal[1]}"
                                if db.should_run_task(sync_key):
                                    db.mark_task_run(sync_key)
                                    return True
                                return False

                            # Monthly reports - only once per month
                            if "monthly_" in filename:
                                sync_key = f"notion_sync_monthly_{today.year}_{today.month:02d}"
                                if db.should_run_task(sync_key):
                                    db.mark_task_run(sync_key)
                                    return True
                                return False

                            # Yearly reports - only once per year
                            if "yearly_" in filename or "1y_" in filename:
                                sync_key = f"notion_sync_yearly_{today.year}"
                                if db.should_run_task(sync_key):
                                    db.mark_task_run(sync_key)
                                    return True
                                return False

                            # Default: sync daily documents
                            return True

                        # Collect all markdown files
                        all_md_files = []
                        for search_path in [output_path, reports_path, research_path]:
                            if search_path.exists():
                                all_md_files.extend(search_path.glob("*.md"))
                                all_md_files.extend(search_path.glob("**/*.md"))

                        # Deduplicate
                        seen = set()
                        md_files = []
                        for f in all_md_files:
                            if f not in seen and "FILE_INDEX" not in f.name and "/archive/" not in str(f).replace("\\", "/"):
                                seen.add(f)
                                md_files.append(f)

                        for filepath in md_files:
                            try:
                                content = filepath.read_text(encoding="utf-8")

                                # Check if document is ready for sync (has proper frontmatter status)
                                # Documents without frontmatter or with status != published/complete should NOT sync
                                try:
                                    if not is_ready_for_sync(content):
                                        skipped_status += 1
                                        continue
                                except Exception as e:
                                    # If frontmatter check fails, skip this file - don't sync unready documents
                                    logger.debug(f"Frontmatter check failed for {filepath.name}: {e}")
                                    skipped_status += 1
                                    continue

                                # Check type-aware schedule
                                doc_type = "journal" if "Journal_" in filepath.name else "reports"
                                # Ensure executor-only files and digests are never published (extra safety)
                                fname_l = filepath.name.lower()
                                if any(p.lower() in fname_l or p.lower() in str(filepath).lower() for p in [
                                    "monitor_",
                                    "data_fetch_",
                                    "digest_",
                                    "digests/",
                                    "_act-",
                                    "act-",
                                ]):
                                    skipped_schedule += 1
                                    continue
                                if not should_sync_doc(filepath, doc_type):
                                    skipped_schedule += 1
                                    continue

                                # Sync the file
                                result = publisher.sync_file(str(filepath), force=False)
                                if result.get("skipped"):
                                    # File unchanged - this is fine
                                    pass
                                else:
                                    published += 1
                                    print(f"  ✓ {filepath.name} → {result.get('type', 'notes')}")

                            except Exception as e:
                                failed += 1
                                logger.debug(f"Failed to sync {filepath.name}: {e}")

                        # Summary
                        if published > 0:
                            print(f"[DAEMON] Published {published} documents to Notion")
                        if skipped_schedule > 0:
                            print(f"[DAEMON] Skipped {skipped_schedule} docs (not scheduled yet)")
                        if skipped_status > 0:
                            print(f"[DAEMON] Skipped {skipped_status} docs (not ready - draft/not AI processed)")
                        if failed > 0:
                            print(f"[DAEMON] Failed to publish {failed} documents")

                        return published, skipped_schedule, skipped_status

                    except ImportError:
                        print("[DAEMON] Notion publisher not available, skipping")
                        return 0, 0, 0
                    except ValueError as e:
                        # Missing API keys
                        print(f"[DAEMON] Notion not configured: {e}")
                        return 0, 0, 0
                    except Exception as notion_err:
                        print(f"[DAEMON] Notion publishing error: {notion_err}")
                        return 0, 0, 0

        # End of post-analysis try block
    except ImportError as e:
        print(f"[DAEMON] Post-analysis skipped (missing module): {e}")
    except Exception as e:
        print(f"[DAEMON] Post-analysis error: {e}")

def interactive_mode(no_ai: bool = False):
    """Simplified interactive menu."""

    MENU = """
┌─────────────────────────────────────────────────────────────┐
│                    GOLD STANDARD                            │
│              Precious Metals Intelligence                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   [1]  RUN ALL ANALYSIS                                     │
│        Daily journal + auto-check monthly/yearly            │
│                                                             │
│   [2]  Quick Daily Update                                   │
│        Just run daily journal (fastest)                     │
│                                                             │
│   [3]  Pre-Market Plan                                      │
│        Generate today's trading blueprint                   │
│                                                             │
│   [4]  Force Regenerate All                                 │
│        Regenerate all reports (ignores existing)            │
│                                                             │
│   [5]  View Status                                          │
│        Check what reports exist                             │
│                                                             │
│   [0]  Exit                                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
"""

    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print_banner()
        print_status()
        print(MENU)

        if no_ai:
            print("  [AI Disabled - running in --no-ai mode]\n")

        choice = input("  Enter choice [0-5]: ").strip()

        if choice == "1":
            run_all(no_ai=no_ai, force=False)
            input("\n  Press Enter to continue...")
        elif choice == "2":
            run_daily(no_ai=no_ai)
            input("\n  Press Enter to continue...")
        elif choice == "3":
            run_premarket(no_ai=no_ai)
            input("\n  Press Enter to continue...")
        elif choice == "4":
            confirm = input("\n  This will regenerate ALL reports. Continue? [y/N]: ").strip().lower()
            if confirm == "y":
                run_all(no_ai=no_ai, force=True)
            input("\n  Press Enter to continue...")
        elif choice == "5":
            print_status()
            input("\n  Press Enter to continue...")
        elif choice == "0":
            print("\n  Goodbye!\n")
            break
        else:
            print("\n  Invalid choice.")
            input("  Press Enter to continue...")


def handle_lifecycle_command(action: str, target_file: str = None, filter_status: str = None):
    """Handle document lifecycle management commands."""
    from pathlib import Path

    from db_manager import get_db
    from scripts.frontmatter import (
        VALID_STATUSES,
        get_document_status,
        is_published,
        promote_status,
        set_document_status,
    )

    project_root = Path(PROJECT_ROOT)
    output_dir = project_root / "output"

    if action == "list":
        # List documents by status
        status_filter = filter_status or "all"
        print(f"\n[DOC] Documents by status: {status_filter}\n")

        md_files = list(output_dir.glob("**/*.md"))
        md_files = [f for f in md_files if "archive" not in str(f).lower()]

        by_status = {}
        for filepath in md_files:
            content = filepath.read_text(encoding="utf-8")
            status = get_document_status(content)
            if status_filter == "all" or status == status_filter:
                if status not in by_status:
                    by_status[status] = []
                by_status[status].append(filepath.relative_to(PROJECT_ROOT))

        for status in VALID_STATUSES:
            if status in by_status:
                print(f"\n  [{status.upper()}] ({len(by_status[status])} files)")
                for f in by_status[status][:10]:  # Show max 10 per status
                    print(f"    - {f}")
                if len(by_status[status]) > 10:
                    print(f"    ... and {len(by_status[status]) - 10} more")
        return

    if action == "status" and target_file:
        # Show status of specific file
        filepath = Path(target_file)
        if not filepath.is_absolute():
            filepath = project_root / target_file
        if not filepath.exists():
            print(f"[ERROR] File not found: {filepath}")
            return

        content = filepath.read_text(encoding="utf-8")
        status = get_document_status(content)
        published = is_published(content)
        print(f"\n[DOC] {filepath.name}")
        print(f"   Status: {status}")
        print(f"   Notion sync: {'[OK] Eligible' if published else '[X] Not eligible (requires published status)'}")
        return

    if action == "promote" and target_file:
        # Promote document to next status
        filepath = Path(target_file)
        if not filepath.is_absolute():
            filepath = project_root / target_file
        if not filepath.exists():
            print(f"[ERROR] File not found: {filepath}")
            return

        content = filepath.read_text(encoding="utf-8")
        old_status = get_document_status(content)
        new_content = promote_status(content, filepath.name)
        new_status = get_document_status(new_content)

        if old_status != new_status:
            filepath.write_text(new_content, encoding="utf-8")
            print(f"[OK] {filepath.name}: {old_status} -> {new_status}")

            # Update database
            db = get_db()
            db.update_document_status(str(filepath), new_status)
        else:
            print(f"  {filepath.name} is already at final status: {old_status}")
        return

    if action == "publish" and target_file:
        # Directly set to published
        filepath = Path(target_file)
        if not filepath.is_absolute():
            filepath = project_root / target_file
        if not filepath.exists():
            print(f"[ERROR] File not found: {filepath}")
            return

        content = filepath.read_text(encoding="utf-8")
        new_content = set_document_status(content, "published", filepath.name)
        filepath.write_text(new_content, encoding="utf-8")
        print(f"[OK] {filepath.name}: published")

        # Update database
        db = get_db()
        db.update_document_status(str(filepath), "published")
        return

    if action == "draft" and target_file:
        # Reset to draft
        filepath = Path(target_file)
        if not filepath.is_absolute():
            filepath = project_root / target_file
        if not filepath.exists():
            print(f"[ERROR] File not found: {filepath}")
            return

        content = filepath.read_text(encoding="utf-8")
        new_content = set_document_status(content, "draft", filepath.name)
        filepath.write_text(new_content, encoding="utf-8")
        print(f"[OK] {filepath.name}: reset to draft")

        # Update database
        db = get_db()
        db.update_document_status(str(filepath), "draft")
        return

    # No file specified
    print("\n[LIFECYCLE] Document Lifecycle Management")
    print("=" * 40)
    print("  Statuses: draft -> in_progress -> review -> published -> archived")
    print("\n  Usage:")
    print("    --lifecycle list                        List all documents by status")
    print("    --lifecycle list --show-status draft    List only draft documents")
    print("    --lifecycle status --file <path>        Show status of specific file")
    print("    --lifecycle promote --file <path>       Promote to next status")
    print("    --lifecycle publish --file <path>       Mark as published (Notion-ready)")
    print("    --lifecycle draft --file <path>         Reset to draft status")
    print("\n  Only 'published' documents are synced to Notion.")


def main():
    parser = argparse.ArgumentParser(
        description="Syndicate CLI - Autonomous precious metals analysis system. Runs continuously by default.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                  # Autonomous daemon mode (1-minute cycles)
    python run.py --once           # Single run and exit
  python run.py --once           # Single run and exit
  python run.py --run            # Run all analysis once
  python run.py --interval-min 5 # Daemon with 5-minute interval
  python run.py --interval 2     # Daemon with 2-hour interval (legacy)
  python run.py --interactive    # Interactive menu
  python run.py --status         # Show current status
  python run.py --no-ai          # Daemon without AI
        """,
    )
    parser.add_argument("--run", "-r", action="store_true", help="Run complete analysis (daily + check monthly/yearly)")
    parser.add_argument("--daily", "-d", action="store_true", help="Quick daily journal update only")
    parser.add_argument("--premarket", "-p", action="store_true", help="Generate pre-market plan")
    parser.add_argument("--force", "-f", action="store_true", help="Force regenerate reports even if they exist")
    parser.add_argument("--status", "-s", action="store_true", help="Show current system status")
    parser.add_argument("--no-ai", action="store_true", help="Disable AI-generated content (Gemini)")
    parser.add_argument("--interactive", "-i", action="store_true", help="Force interactive mode")
    parser.add_argument("--once", action="store_true", help="Run once and exit (no daemon)")
    parser.add_argument("--wait", action="store_true", help="Wait (bounded by timeout) for post-analysis tasks to complete before exit")
    parser.add_argument("--wait-forever", action="store_true", help="Wait indefinitely until no tasks, no new insights, and all documents are published to Notion before exiting")
    parser.add_argument(
        "--interval", type=int, default=0, help="Hours between daemon runs (legacy, default: 0 = use minutes)"
    )
    parser.add_argument("--interval-min", type=int, default=240, help="Minutes between daemon runs (default: 240 -> 4 hours)")

    # Feature toggles
    parser.add_argument(
        "--toggle",
        choices=["notion", "tasks", "insights"],
        help="Toggle a feature on/off (use with --enable or --disable)",
    )
    parser.add_argument("--enable", action="store_true", help="Enable the specified feature")
    parser.add_argument("--disable", action="store_true", help="Disable the specified feature")
    parser.add_argument("--show-toggles", action="store_true", help="Show current feature toggle states")

    # Document lifecycle management
    parser.add_argument(
        "--lifecycle",
        choices=["status", "promote", "publish", "draft", "list"],
        help="Document lifecycle management",
    )
    parser.add_argument("--file", type=str, help="Target file for lifecycle command")
    parser.add_argument("--show-status", type=str, help="Show documents by status (draft/in_progress/published)")

    # Legacy support for --mode
    parser.add_argument(
        "--mode",
        "-m",
        choices=["daily", "weekly", "monthly", "yearly", "premarket"],
        help="(Legacy) Run specific mode directly",
    )

    args = parser.parse_args()

    # Change to project root
    os.chdir(PROJECT_ROOT)

    # Handle commands
    if args.status:
        print_banner()
        print_status()
        return

    # Feature toggle management
    if args.show_toggles:
        from db_manager import get_db

        db = get_db()
        print("\n┌─────────────────────────────────────────────────────────────┐")
        print("│                     FEATURE TOGGLES                          │")
        print("├─────────────────────────────────────────────────────────────┤")
        notion_status = "✅ ENABLED" if db.is_notion_publishing_enabled() else "⏸️  DISABLED"
        tasks_status = "✅ ENABLED" if db.is_task_execution_enabled() else "⏸️  DISABLED"
        insights_status = "✅ ENABLED" if db.is_insights_extraction_enabled() else "⏸️  DISABLED"
        print(f"│  Notion Publishing:    {notion_status:<20}             │")
        print(f"│  Task Execution:       {tasks_status:<20}             │")
        print(f"│  Insights Extraction:  {insights_status:<20}             │")
        print("├─────────────────────────────────────────────────────────────┤")
        print("│  Toggle: python run.py --toggle notion --disable           │")
        print("│          python run.py --toggle notion --enable            │")
        print("└─────────────────────────────────────────────────────────────┘")
        return

    if args.toggle:
        from db_manager import get_db

        db = get_db()
        if not args.enable and not args.disable:
            print("Error: --toggle requires --enable or --disable")
            return
        enabled = args.enable
        if args.toggle == "notion":
            db.set_notion_publishing_enabled(enabled)
            print(f"Notion publishing {'ENABLED' if enabled else 'DISABLED'}")
        elif args.toggle == "tasks":
            db.set_task_execution_enabled(enabled)
            print(f"Task execution {'ENABLED' if enabled else 'DISABLED'}")
        elif args.toggle == "insights":
            db.set_insights_extraction_enabled(enabled)
            print(f"Insights extraction {'ENABLED' if enabled else 'DISABLED'}")
        return

    # Single run mode (--once) - execute once and exit cleanly
    if args.once:
        print_banner()
        print("[ONCE] Running single analysis cycle...")
        run_all(no_ai=args.no_ai, force=args.force)
        # Default behavior: wait-forever unless user explicitly disables
        wait_forever_flag = args.wait_forever or (not args.wait and not args.wait_forever)
        # Run post-analysis tasks (force inline if waiting and optionally wait or wait-forever)
        _run_post_analysis_tasks(
            force_inline=(args.wait or wait_forever_flag),
            wait_for_completion=args.wait,
            wait_forever=wait_forever_flag,
        )
        print("[ONCE] Single run complete. Exiting.")
        return

    # Document lifecycle management
    if args.lifecycle:
        print_banner()
        handle_lifecycle_command(args.lifecycle, args.file, args.show_status)
        return

    # Legacy mode support
    if args.mode:
        print_banner()
        if args.mode == "daily":
            run_daily(no_ai=args.no_ai)
        elif args.mode == "weekly":
            run_weekly(no_ai=args.no_ai)
        elif args.mode == "monthly":
            run_monthly(no_ai=args.no_ai)
        elif args.mode == "yearly":
            run_yearly(no_ai=args.no_ai)
        elif args.mode == "premarket":
            run_premarket(no_ai=args.no_ai)
        return

    if args.run:
        print_banner()
        run_all(no_ai=args.no_ai, force=args.force)
        return

    if args.daily:
        print_banner()
        run_daily(no_ai=args.no_ai)
        return

    if args.premarket:
        print_banner()
        run_premarket(no_ai=args.no_ai)
        return

    # Interactive mode if explicitly requested
    if args.interactive:
        interactive_mode(no_ai=args.no_ai)
        return

    # Added logic for --once flag: Run all analysis once and exit
    if args.once:
        print_banner()
        run_all(no_ai=args.no_ai, force=args.force)
        _run_post_analysis_tasks(force_inline=args.wait, wait_for_completion=args.wait)  # Execute post-analysis tasks for a single run
        return
    # Default: Autonomous daemon mode
    print_banner()
    run_daemon(no_ai=args.no_ai, interval_hours=args.interval, interval_minutes=args.interval_min)


if __name__ == "__main__":
    main()
