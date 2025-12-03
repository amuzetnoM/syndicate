#!/usr/bin/env python3
"""
Gold Standard CLI
Unified entry point with intelligent report management.
Runs all analysis with automatic redundancy control.

Default mode: Autonomous daemon that runs analysis every 4 hours.
Use --once for single execution, or --interactive for menu.
"""
import os
import sys
import argparse
import signal
import time
from datetime import date, datetime

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)


def ensure_venv():
    """
    Ensure we're running inside the virtual environment.
    If not, re-execute this script with the venv Python.
    """
    # Check if already in venv
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        return  # Already in venv
    
    # Look for venv directories
    venv_dirs = ['venv312', 'venv', '.venv']
    venv_python = None
    
    for venv_name in venv_dirs:
        venv_path = os.path.join(PROJECT_ROOT, venv_name)
        if os.path.isdir(venv_path):
            # Windows vs Unix paths
            if sys.platform == 'win32':
                candidate = os.path.join(venv_path, 'Scripts', 'python.exe')
            else:
                candidate = os.path.join(venv_path, 'bin', 'python')
            
            if os.path.isfile(candidate):
                venv_python = candidate
                break
    
    if venv_python:
        print(f"[VENV] Activating virtual environment: {os.path.basename(os.path.dirname(os.path.dirname(venv_python)))}")
        # Re-execute with venv python
        os.execv(venv_python, [venv_python] + sys.argv)
    else:
        print("[WARN] No virtual environment found. Running with system Python.")
        print("       Consider creating venv312: python -m venv venv312")


# Ensure venv before importing project modules
ensure_venv()

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
    print("=" * 60 + "\n")


def run_daily(no_ai: bool = False) -> bool:
    """Run the daily journal via main.py."""
    print("\n>> Running Daily Journal Analysis...\n")
    cmd_parts = [sys.executable, "main.py", "--once"]
    if no_ai:
        cmd_parts.append("--no-ai")
    return os.system(" ".join(cmd_parts)) == 0


def run_weekly(no_ai: bool = False) -> bool:
    """Run the weekly rundown via split_reports.py."""
    print("\n>> Generating Weekly Report...\n")
    cmd_parts = [sys.executable, "scripts/split_reports.py", "--mode", "weekly", "--once"]
    if no_ai:
        cmd_parts.append("--no-ai")
    return os.system(" ".join(cmd_parts)) == 0


def run_monthly(no_ai: bool = False) -> bool:
    """Run the monthly report via split_reports.py."""
    print("\n>> Generating Monthly Report...\n")
    cmd_parts = [sys.executable, "scripts/split_reports.py", "--mode", "monthly", "--once"]
    if no_ai:
        cmd_parts.append("--no-ai")
    return os.system(" ".join(cmd_parts)) == 0


def run_yearly(no_ai: bool = False) -> bool:
    """Run the yearly report via split_reports.py."""
    print("\n>> Generating Yearly Report...\n")
    cmd_parts = [sys.executable, "scripts/split_reports.py", "--mode", "yearly", "--once"]
    if no_ai:
        cmd_parts.append("--no-ai")
    return os.system(" ".join(cmd_parts)) == 0


def run_premarket(no_ai: bool = False) -> bool:
    """Run the pre-market plan via pre_market.py."""
    print("\n>> Generating Pre-Market Plan...\n")
    cmd_parts = [sys.executable, "scripts/pre_market.py"]
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
    
    # 1. Always run daily journal (will update/create for today)
    print("\n[1/5] DAILY JOURNAL")
    print("-" * 40)
    results['daily'] = run_daily(no_ai=no_ai)
    
    # 2. Pre-market plan (if not already done today)
    print("\n[2/5] PRE-MARKET PLAN")
    print("-" * 40)
    if not db.has_premarket_for_date(today.isoformat()) or force:
        results['premarket'] = run_premarket(no_ai=no_ai)
    else:
        print("  [SKIP] Pre-market plan already exists for today")
        results['premarket'] = True
    
    # 3. Weekly report (on weekends or if forced or missing)
    print("\n[3/5] WEEKLY REPORT")
    print("-" * 40)
    is_weekend = iso_cal[2] >= 6  # Saturday = 6, Sunday = 7
    if not db.has_weekly_report(today.year, iso_cal[1]) and (is_weekend or force):
        results['weekly'] = run_weekly(no_ai=no_ai)
    elif db.has_weekly_report(today.year, iso_cal[1]):
        print(f"  [SKIP] Weekly report for Week {iso_cal[1]} already exists")
        results['weekly'] = True
    else:
        print("  [SKIP] Not weekend. Weekly reports generated on Sat/Sun")
        results['weekly'] = True
    
    # 4. Monthly report (check if exists for current month)
    print("\n[4/5] MONTHLY REPORT")
    print("-" * 40)
    if not db.has_monthly_report(today.year, today.month) or force:
        print(f"  Generating report for {today.year}-{today.month:02d}...")
        results['monthly'] = run_monthly(no_ai=no_ai)
    else:
        print(f"  [SKIP] Monthly report for {today.year}-{today.month:02d} already exists")
        results['monthly'] = True
    
    # 5. Yearly report (check if exists for current year)
    print("\n[5/5] YEARLY REPORT")
    print("-" * 40)
    if not db.has_yearly_report(today.year) or force:
        print(f"  Generating report for {today.year}...")
        results['yearly'] = run_yearly(no_ai=no_ai)
    else:
        print(f"  [SKIP] Yearly report for {today.year} already exists")
        results['yearly'] = True
    
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
    Run Gold Standard as an autonomous daemon.
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
        from scripts.insights_engine import InsightsExtractor
        from scripts.task_executor import TaskExecutor
        from scripts.file_organizer import FileOrganizer
        insights_available = True
        print("[DAEMON] Insights & Task systems loaded")
    except ImportError as e:
        insights_available = False
        print(f"[DAEMON] Insights systems not available: {e}")
    
    # Run immediately on startup
    print("[DAEMON] Running initial analysis cycle...\n")
    run_all(no_ai=no_ai, force=False)
    
    # Run post-analysis tasks if available
    if insights_available and not no_ai:
        _run_post_analysis_tasks()
    
    # Schedule recurring runs
    if use_minutes:
        schedule.every(interval_value).minutes.do(_daemon_cycle, no_ai=no_ai, run_tasks=insights_available and not no_ai)
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


def _run_post_analysis_tasks():
    """Run insights extraction, task execution, and file organization."""
    try:
        from scripts.insights_engine import InsightsExtractor
        from scripts.task_executor import TaskExecutor
        from scripts.file_organizer import FileOrganizer
        import google.generativeai as genai
        from pathlib import Path
        import os
        
        # Get config-like object
        class RuntimeConfig:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            OUTPUT_DIR = os.path.join(BASE_DIR, "output")
        
        config = RuntimeConfig()
        
        # Simple logger
        import logging
        logger = logging.getLogger("GoldStandard.Daemon")
        
        # Try to get model
        model = None
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("models/gemini-pro-latest")
            except Exception:
                pass
        
        # 1. Extract insights from today's reports
        print("[DAEMON] Extracting insights from reports...")
        extractor = InsightsExtractor(config, logger, model)
        reports_dir = Path(config.OUTPUT_DIR) / "reports"
        entities, actions = extractor.process_all_reports(reports_dir)
        
        # Save insights to database
        from db_manager import get_db
        db = get_db()
        
        for entity in entities:
            db.save_entity_insight(
                entity.entity_name,
                entity.entity_type,
                entity.context,
                entity.relevance_score,
                entity.source_report,
                str(entity.metadata)
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
                str(action.metadata)
            )
        
        print(f"[DAEMON] Extracted {len(entities)} entities, {len(actions)} actions")
        
        # 2. Execute pending tasks
        if model:
            print("[DAEMON] Executing pending tasks...")
            executor = TaskExecutor(config, logger, model, extractor)
            results = executor.execute_all_pending(max_tasks=10)
            
            # Log execution results
            for result in results:
                db.log_task_execution(
                    result.action_id,
                    result.success,
                    str(result.result_data),
                    result.execution_time_ms,
                    result.error_message,
                    str(result.artifacts) if result.artifacts else None
                )
            
            print(f"[DAEMON] Executed {len(results)} tasks")
        
        # 3. Organize files
        print("[DAEMON] Organizing files...")
        organizer = FileOrganizer(config, logger)
        org_results = organizer.run_maintenance(archive_days=7)
        print(f"[DAEMON] Organized {org_results['organized']} files, archived {org_results['archived']}")
        
        # 4. Apply frontmatter to all output files (FINAL STEP)
        print("[DAEMON] Applying frontmatter tags...")
        try:
            from scripts.frontmatter import add_frontmatter, has_frontmatter
            
            output_path = Path(config.OUTPUT_DIR)
            reports_path = output_path / "reports"
            frontmatter_count = 0
            
            # Process all markdown files in output directory
            for md_file in list(output_path.glob("*.md")) + list(reports_path.glob("*.md")) + list(reports_path.glob("**/*.md")):
                try:
                    content = md_file.read_text(encoding='utf-8')
                    
                    # Skip if already has frontmatter
                    if has_frontmatter(content):
                        continue
                    
                    # Add frontmatter based on filename
                    updated = add_frontmatter(content, md_file.name)
                    md_file.write_text(updated, encoding='utf-8')
                    frontmatter_count += 1
                except Exception as fm_err:
                    logger.debug(f"Frontmatter failed for {md_file.name}: {fm_err}")
            
            print(f"[DAEMON] Applied frontmatter to {frontmatter_count} files")
        except ImportError:
            print("[DAEMON] Frontmatter module not available, skipping")
        except Exception as fm_err:
            print(f"[DAEMON] Frontmatter error: {fm_err}")
        
        # 5. Publish to Notion
        print("[DAEMON] Publishing to Notion...")
        try:
            from scripts.notion_publisher import sync_all_outputs
            
            results = sync_all_outputs()
            success_count = len(results.get('success', []))
            failed_count = len(results.get('failed', []))
            
            if success_count > 0:
                print(f"[DAEMON] Published {success_count} files to Notion")
            if failed_count > 0:
                print(f"[DAEMON] Failed to publish {failed_count} files")
        except ImportError:
            print("[DAEMON] Notion publisher not available, skipping")
        except ValueError as e:
            # Missing API keys
            print(f"[DAEMON] Notion not configured: {e}")
        except Exception as notion_err:
            print(f"[DAEMON] Notion publishing error: {notion_err}")
        
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
        os.system('cls' if os.name == 'nt' else 'clear')
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
            if confirm == 'y':
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


def main():
    parser = argparse.ArgumentParser(
        description="Gold Standard CLI - Autonomous precious metals analysis system. Runs continuously by default.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                  # Autonomous daemon mode (1-minute cycles)
  python run.py --once           # Single run and exit
  python run.py --run            # Run all analysis once
  python run.py --interval-min 5 # Daemon with 5-minute interval
  python run.py --interval 2     # Daemon with 2-hour interval (legacy)
  python run.py --interactive    # Interactive menu
  python run.py --status         # Show current status
  python run.py --no-ai          # Daemon without AI
        """
    )
    parser.add_argument('--run', '-r', action='store_true',
                       help='Run complete analysis (daily + check monthly/yearly)')
    parser.add_argument('--daily', '-d', action='store_true',
                       help='Quick daily journal update only')
    parser.add_argument('--premarket', '-p', action='store_true',
                       help='Generate pre-market plan')
    parser.add_argument('--force', '-f', action='store_true',
                       help='Force regenerate reports even if they exist')
    parser.add_argument('--status', '-s', action='store_true',
                       help='Show current system status')
    parser.add_argument('--no-ai', action='store_true',
                       help='Disable AI-generated content (Gemini)')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Force interactive mode')
    parser.add_argument('--once', action='store_true',
                       help='Run once and exit (no daemon)')
    parser.add_argument('--interval', type=int, default=0,
                       help='Hours between daemon runs (legacy, default: 0 = use minutes)')
    parser.add_argument('--interval-min', type=int, default=1,
                       help='Minutes between daemon runs (default: 1)')
    
    # Legacy support for --mode
    parser.add_argument('--mode', '-m', choices=['daily', 'weekly', 'monthly', 'yearly', 'premarket'],
                       help='(Legacy) Run specific mode directly')

    args = parser.parse_args()
    
    # Change to project root
    os.chdir(PROJECT_ROOT)
    
    # Handle commands
    if args.status:
        print_banner()
        print_status()
        return
    
    # Legacy mode support
    if args.mode:
        print_banner()
        if args.mode == 'daily':
            run_daily(no_ai=args.no_ai)
        elif args.mode == 'weekly':
            run_weekly(no_ai=args.no_ai)
        elif args.mode == 'monthly':
            run_monthly(no_ai=args.no_ai)
        elif args.mode == 'yearly':
            run_yearly(no_ai=args.no_ai)
        elif args.mode == 'premarket':
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
    
    # Default: Autonomous daemon mode
    print_banner()
    run_daemon(no_ai=args.no_ai, interval_hours=args.interval, interval_minutes=args.interval_min)


if __name__ == '__main__':
    main()
